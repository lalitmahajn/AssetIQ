const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 0. Cleanup Lock Files (Fixes "Profile in use" errors)
const sessionPath = '/app/session';
function cleanupLocks(dir) {
    if (!fs.existsSync(dir)) return;
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const fullPath = path.join(dir, file);
        if (fs.lstatSync(fullPath).isDirectory()) {
            cleanupLocks(fullPath);
        } else if (file.startsWith('Singleton')) {
            try {
                console.log(`Removing lock file: ${fullPath}`);
                fs.unlinkSync(fullPath);
            } catch (e) {
                console.error(`Failed to remove ${fullPath}: ${e.message}`);
            }
        }
    }
}

try {
    cleanupLocks(sessionPath);
} catch (err) {
    console.error('Lock cleanup failed (non-critical):', err.message);
}

// 1. Database Setup
const pool = new Pool({
    connectionString: process.env.PLANT_DB_URL || 'postgresql://assetiq:assetiq@postgres:5432/assetiq_plant'
});

// 2. WhatsApp Client Setup
let isClientReady = false;
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: '/app/session' // Persist session in Docker volume
    }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
        ]
    }
});

client.on('qr', async (qr) => {
    console.log('--- SCAN QR CODE WITH WHATSAPP ---');
    qrcode.generate(qr, { small: true });

    // Save QR code to database for UI access
    try {
        const query = `
            INSERT INTO system_config (config_key, config_value, updated_at_utc)
            VALUES ('whatsappQRCode', $1::jsonb, NOW())
            ON CONFLICT (config_key) 
            DO UPDATE SET config_value = $1::jsonb, updated_at_utc = NOW();
        `;
        await pool.query(query, [JSON.stringify(qr)]);
        console.log('QR code saved to database for UI access.');
    } catch (err) {
        console.error('Failed to save QR code:', err.message);
    }
});

client.on('ready', async () => {
    isClientReady = true;
    console.log('WhatsApp Client is Ready!');

    // Clear QR code from database (no longer needed)
    try {
        await pool.query("DELETE FROM system_config WHERE config_key = 'whatsappQRCode'");

        // [DEBUG] Log all available chats to help user verify names
        const chats = await client.getChats();
        console.log("---------------------------------------------------");
        console.log("AVAILABLE WHATSAPP CHATS (Groups & Contacts):");
        chats.forEach(c => {
            if (c.isGroup) console.log(`[GROUP] Name: "${c.name}" | ID: ${c.id._serialized}`);
            else console.log(`[USER]  Name: "${c.name}" | ID: ${c.id._serialized}`);
        });
        console.log("---------------------------------------------------");

    } catch (err) {
        console.error('Failed to clear QR code or log chats:', err.message);
    }
});

client.on('disconnected', (reason) => {
    isClientReady = false;
    console.log('Client was logged out', reason);
});

client.on('auth_failure', (msg) => {
    isClientReady = false;
    console.error('AUTHENTICATION FAILURE', msg);
});

async function startPolling() {
    console.log('Started polling whatsapp_queue...');
    setInterval(async () => {
        try {
            // 1. Check for Logout Request (Always check this)
            const logoutCheck = await pool.query(
                "SELECT * FROM system_config WHERE config_key = 'whatsappLogoutRequest'"
            );
            if (logoutCheck.rows.length > 0) {
                console.log('Logout request detected! Logging out...');
                isClientReady = false; // Mark as not ready during logout
                try {
                    await client.logout();
                    console.log('Logout successful.');
                } catch (e) {
                    console.error('Logout failed:', e.message);
                }
                // Delete the request
                await pool.query("DELETE FROM system_config WHERE config_key = 'whatsappLogoutRequest'");
                // Also clear heartbeats/QR to force a clean state
                await pool.query("DELETE FROM system_config WHERE config_key = 'whatsappQRCode'");
                console.log('Cleaning up session files...');

                // Reinitialize client to generate new QR code
                console.log('Reinitializing client for fresh QR code...');
                try {
                    await client.initialize();
                } catch (e) {
                    console.error('Reinitialize failed:', e.message);
                }
            }

            // 2. Poll for PENDING messages (Only if client is ready)
            if (isClientReady) {
                const res = await pool.query(
                    "SELECT * FROM whatsapp_queue WHERE status = 'PENDING' ORDER BY created_at_utc ASC LIMIT 5"
                );

                for (const row of res.rows) {
                    await processMessage(row);
                }
            }
        } catch (err) {
            console.error('Polling Error:', err);
        }
    }, 2000); // Every 2 seconds
}

async function startHeartbeat() {
    console.log('Started heartbeat service...');

    const sendPulse = async () => {
        try {
            let state = 'DISCONNECTED';
            if (isClientReady) {
                try {
                    const rawState = await client.getState();
                    // Normalize state - rawState can be string, object, null, or undefined
                    if (!rawState) {
                        state = 'CONNECTED'; // Client is ready but getState returned nothing
                    } else if (typeof rawState === 'string') {
                        // Normalize known connected states to 'CONNECTED'
                        const connectedStates = ['CONNECTED', 'PAIRED', 'AUTHENTICATED'];
                        state = connectedStates.includes(rawState.toUpperCase()) ? 'CONNECTED' : rawState.toUpperCase();
                    } else if (typeof rawState === 'object') {
                        // Some library versions return an object with a state property
                        state = rawState.state || rawState._state || 'CONNECTED';
                    } else {
                        state = 'CONNECTED';
                    }
                } catch (e) {
                    // If client is ready but getState fails, it's likely still connected
                    console.warn('getState() failed but client is ready:', e.message);
                    state = 'CONNECTED';
                }
            } else {
                // If we have a QR code in DB, we are waiting for scan
                const qrCheck = await pool.query("SELECT * FROM system_config WHERE config_key = 'whatsappQRCode'");
                if (qrCheck.rows.length > 0) {
                    state = 'UNPAIRED';
                } else {
                    state = 'INITIALIZING';
                }
            }

            const heartbeatData = JSON.stringify({
                ts: Date.now(),
                state: state
            });

            await pool.query(`
                INSERT INTO system_config (config_key, config_value, updated_at_utc)
                VALUES ('whatsappHeartbeat', $1, NOW())
                ON CONFLICT (config_key) 
                DO UPDATE SET config_value = $1, updated_at_utc = NOW();
            `, [heartbeatData]);

            console.log(`Heartbeat sent: ${state}`);
        } catch (err) {
            console.error('Heartbeat Failed:', err.message);
        }
    };

    // Run once immediately
    await sendPulse();
    // Then every 30 seconds
    setInterval(sendPulse, 30000);
}

async function processMessage(row) {
    const { id, phone_number, message, sla_state } = row;
    try {
        console.log(`Processing message (Queue ID: ${id}, SLA: ${sla_state || 'N/A'})...`);

        // Split by comma and clean up whitespace
        const rawTargets = phone_number.split(',').map(t => t.trim()).filter(t => t.length > 0);
        let successCount = 0;
        let failCount = 0;
        let skippedCount = 0;

        for (const rawTarget of rawTargets) {
            try {
                // Parse conditional format: "GroupName:SLAState" or just "GroupName"
                let targetName = rawTarget;
                let requiredSlaState = null;

                if (rawTarget.includes(':')) {
                    const parts = rawTarget.split(':');
                    targetName = parts[0].trim();
                    requiredSlaState = parts[1].trim().toUpperCase();
                }

                // Check SLA condition
                if (requiredSlaState && sla_state) {
                    // [UPDATED] Check match against ANY of the states in the comma-separated sla_state
                    // e.g. required="WARNING", actual="OK,WARNING" => MATCH
                    const currentStates = sla_state.toUpperCase().split(',').map(s => s.trim());

                    // DEBUG LOG
                    console.log(`[DEBUG] Checking ${targetName}: Required='${requiredSlaState}', Current=[${currentStates.map(s => `'${s}'`).join(', ')}]`);

                    if (!currentStates.includes(requiredSlaState)) {
                        console.log(`Skipping ${targetName} (requires ${requiredSlaState}, current: ${sla_state})`);
                        skippedCount++;
                        continue;
                    }
                }

                let targetId = '';

                if (targetName.includes('@g.us') || targetName.includes('@c.us')) {
                    targetId = targetName;
                } else if (/^\+?\d+$/.test(targetName)) {
                    let cleanNumber = targetName.replace('+', '').replace(/\s/g, '');
                    targetId = `${cleanNumber}@c.us`;
                } else {
                    // Group/Contact Name search
                    console.log(`Searching for chat named: "${targetName}"...`);
                    const chats = await client.getChats();
                    const targetChat = chats.find(c => c.name === targetName);

                    if (!targetChat) {
                        console.error(`Chat not found with name: ${targetName}`);
                        failCount++;
                        continue;
                    }
                    targetId = targetChat.id._serialized;
                }

                await client.sendMessage(targetId, message);
                console.log(`Successfully sent message to ${targetId}`);
                successCount++;
            } catch (innerErr) {
                console.error(`Failed to send to ${rawTarget}:`, innerErr.message);
                failCount++;
            }
        }

        if (successCount > 0 || skippedCount === rawTargets.length) {
            // Mark as SENT if at least one succeeded, or all were intentionally skipped
            await pool.query(
                "UPDATE whatsapp_queue SET status = 'SENT', sent_at_utc = NOW() WHERE id = $1",
                [id]
            );
            console.log(`Message ${id} complete. Sent: ${successCount}, Failed: ${failCount}, Skipped: ${skippedCount}`);
        } else {
            throw new Error(`Failed to send to all ${rawTargets.length} targets.`);
        }

    } catch (err) {
        console.error(`Failed to process message ${id}:`, err.message);
        await pool.query(
            "UPDATE whatsapp_queue SET status = 'FAILED' WHERE id = $1",
            [id]
        );
    }
}

client.initialize();
startPolling();
startHeartbeat();

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

client.on('qr', (qr) => {
    console.log('--- SCAN QR CODE WITH WHATSAPP ---');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('WhatsApp Client is Ready!');
    startPolling();
});

client.on('auth_failure', (msg) => {
    console.error('AUTHENTICATION FAILURE', msg);
});

async function startPolling() {
    console.log('Started polling whatsapp_queue...');
    setInterval(async () => {
        try {
            const res = await pool.query(
                "SELECT * FROM whatsapp_queue WHERE status = 'PENDING' ORDER BY created_at_utc ASC LIMIT 5"
            );

            for (const row of res.rows) {
                await processMessage(row);
            }
        } catch (err) {
            console.error('Polling Error:', err);
        }
    }, 10000); // Every 10 seconds
}

async function processMessage(row) {
    const { id, phone_number, message } = row;
    try {
        console.log(`Processing message for ${phone_number} (Queue ID: ${id})...`);
        
        let targetId = '';

        if (phone_number.includes('@g.us') || phone_number.includes('@c.us')) {
            targetId = phone_number;
        } else if (/^\+?\d+$/.test(phone_number.trim())) {
            let cleanNumber = phone_number.replace('+', '').replace(/\s/g, '');
            targetId = `${cleanNumber}@c.us`;
        } else {
            // Group/Contact Name search
            console.log(`Searching for chat named: "${phone_number}"...`);
            const chats = await client.getChats();
            const targetChat = chats.find(c => c.name === phone_number);
            
            if (!targetChat) {
                throw new Error(`Chat not found with name: ${phone_number}`);
            }
            targetId = targetChat.id._serialized;
        }

        // Revert to client.sendMessage (more resilient to 'markedUnread' errors in some versions)
        await client.sendMessage(targetId, message);
        
        await pool.query(
            "UPDATE whatsapp_queue SET status = 'SENT', sent_at_utc = NOW() WHERE id = $1",
            [id]
        );
        console.log(`Successfully sent message ${id} to ${targetId}`);
    } catch (err) {
        console.error(`Failed to send message ${id}:`, err.message);
        await pool.query(
            "UPDATE whatsapp_queue SET status = 'FAILED' WHERE id = $1",
            [id]
        );
    }
}

client.initialize();

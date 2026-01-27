import { useEffect, useState } from "react";
import QRCode from "react-qr-code";
import { apiGet, apiPost } from "../../api";



const SLA_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const SLA_DEFAULTS = { LOW: 240, MEDIUM: 240, HIGH: 120, CRITICAL: 120 };
const SLA_WARNING_THRESHOLD = 60; // minutes, fixed
function getSlaMatrixRows(slaDurations) {
    return SLA_PRIORITIES.map(priority => {
        const initial = parseInt(slaDurations[priority]) || SLA_DEFAULTS[priority];
        const warning = Math.max(0, initial - SLA_WARNING_THRESHOLD);
        return {
            priority,
            initial,
            warning,
            breached: 0,
        };
    });
}

export default function StationConfig() {
    const [config, setConfig] = useState({
        plantName: "Loading...",
        stopQueueVisible: true,
        autoLogoutMinutes: 30,
        whatsappEnabled: false,
        whatsappTargetPhone: "",
        whatsappMessageTemplate: "",
        whatsappCloseMessageTemplate: "",
        whatsappHeartbeat: null,
        whatsappQRCode: null,
        slaDurations: { ...SLA_DEFAULTS },
    });

    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState("");
    const [showQRModal, setShowQRModal] = useState(false);

    useEffect(() => {
        loadConfig();
        // Auto-refresh only WhatsApp status every 15 seconds (not the whole config)
        const interval = setInterval(() => {
            refreshWhatsAppStatus();
        }, 15000);
        return () => clearInterval(interval);
    }, []);

    async function loadConfig() {
        try {
            const data = await apiGet("/master/config");
            setConfig(prev => ({ ...prev, ...data }));
        } catch (e) {
            console.error("Failed to load config", e);
        }
    }

    // Only refresh WhatsApp status fields, not editable fields
    async function refreshWhatsAppStatus() {
        try {
            const data = await apiGet("/master/config");
            // Only update status fields, preserve user's unsaved edits
            setConfig(prev => ({
                ...prev,
                whatsappHeartbeat: data.whatsappHeartbeat,
                whatsappQRCode: data.whatsappQRCode,
            }));
        } catch (e) {
            console.error("Failed to refresh WhatsApp status", e);
        }
    }

    function handleChange(field, val) {
        setConfig({ ...config, [field]: val });
        setMsg("");
    }

    function handleSlaDurationChange(priority, value) {
        let v = value.replace(/[^0-9]/g, "");
        v = v ? Math.max(1, Math.min(1440, parseInt(v))) : "";
        setConfig(cfg => ({
            ...cfg,
            slaDurations: { ...cfg.slaDurations, [priority]: v },
        }));
        setMsg("");
    }

    function handleResetSlaDurations() {
        setConfig(cfg => ({ ...cfg, slaDurations: { ...SLA_DEFAULTS } }));
        setMsg("SLA durations reset to default.");
    }

    async function handleSave() {
        setSaving(true);
        setMsg("");
        const minutes = parseInt(config.autoLogoutMinutes);
        if (isNaN(minutes) || minutes < 1) {
            setMsg("Error: Auto Logout must be at least 1 minute.");
            setSaving(false);
            return;
        }
        // Validate SLA durations
        for (const p of SLA_PRIORITIES) {
            const v = config.slaDurations[p];
            if (!v || isNaN(v) || v < 1 || v > 1440) {
                setMsg(`Error: SLA for ${p} must be 1-1440 minutes.`);
                setSaving(false);
                return;
            }
        }
        try {
            const res = await apiPost("/master/config", {
                plantName: config.plantName,
                stopQueueVisible: config.stopQueueVisible,
                autoLogoutMinutes: minutes,
                whatsappEnabled: config.whatsappEnabled,
                whatsappTargetPhone: config.whatsappTargetPhone,
                whatsappMessageTemplate: config.whatsappMessageTemplate,
                whatsappCloseMessageTemplate: config.whatsappCloseMessageTemplate,
                whatsappWarningMessageTemplate: config.whatsappWarningMessageTemplate,
                whatsappBreachMessageTemplate: config.whatsappBreachMessageTemplate,
                slaDurations: config.slaDurations,
            });
            setMsg("Configuration saved successfully!");
            if (res.updated) {
                setConfig(prev => ({ ...prev, ...res.updated }));
            }
            window.dispatchEvent(new Event("config:updated"));
        } catch (e) {
            setMsg("Error: " + String(e));
        } finally {
            setSaving(false);
        }
    }

    async function handleLogout() {
        if (!window.confirm("Are you sure you want to logout from WhatsApp? This will clear your session and you will need to scan the QR code again.")) return;

        setSaving(true);
        try {
            await apiPost("/master/config", {
                whatsappLogoutRequest: "true"
            });
            setMsg("Logout request sent. Please refresh in a few seconds.");
            // Refresh config to see if it's already cleared or will be
            setTimeout(loadConfig, 3000);
        } catch (e) {
            setMsg("Error: " + String(e));
        } finally {
            setSaving(false);
        }
    }

    async function handleSimulate(type) {
        setSaving(true);
        setMsg("");
        try {
            let endpoint = '';
            if (type === 'warning') endpoint = '/master/simulate/sla_warning';
            else if (type === 'breach') endpoint = '/master/simulate/sla_breach';
            else if (type === 'stop') endpoint = '/master/simulate/stop';

            const res = await apiPost(endpoint, {});
            if (res.status === 'ok') {
                setMsg("Simulation triggered! " + res.message);
            } else {
                setMsg("Error: " + res.message);
            }
        } catch (e) {
            setMsg("Error: " + String(e));
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-xl font-bold text-gray-800 mb-4">Station Configuration</h3>

            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
                <p className="text-yellow-700 text-sm">
                    <strong>Note:</strong> Most of these settings are currently loaded from <code>.env</code> files.
                    UI overrides will be enabled in the next major update.
                </p>
            </div>

            <div className="space-y-4 max-w-lg">
                {/* SLA Duration Matrix (Initial, Warning, Breached) */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">SLA Durations (Minutes) by Priority & State</label>
                    <div className="overflow-x-auto">
                        <table className="min-w-full border text-xs">
                            <thead>
                                <tr className="bg-gray-50">
                                    <th className="border px-2 py-1 text-left">SLA State</th>
                                    {SLA_PRIORITIES.map(p => (
                                        <th key={p} className="border px-2 py-1">{p}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {/* Initial SLA row (editable) */}
                                <tr>
                                    <td className="border px-2 py-1 font-medium">Initial</td>
                                    {getSlaMatrixRows(config.slaDurations).map(row => (
                                        <td key={row.priority} className="border px-2 py-1">
                                            <input
                                                type="number"
                                                min={1}
                                                max={1440}
                                                className="w-20 border rounded p-1 text-xs"
                                                value={row.initial}
                                                onChange={e => handleSlaDurationChange(row.priority, e.target.value)}
                                            />
                                        </td>
                                    ))}
                                </tr>
                                {/* Warning SLA row (read-only) */}
                                <tr>
                                    <td className="border px-2 py-1 font-medium">WARNING</td>
                                    {getSlaMatrixRows(config.slaDurations).map(row => (
                                        <td key={row.priority} className="border px-2 py-1 bg-yellow-50 text-yellow-900">
                                            <input
                                                type="number"
                                                className="w-20 border rounded p-1 text-xs bg-yellow-50"
                                                value={row.warning}
                                                readOnly
                                                tabIndex={-1}
                                            />
                                        </td>
                                    ))}
                                </tr>
                                {/* Breached SLA row (always 0, read-only) */}
                                <tr>
                                    <td className="border px-2 py-1 font-medium">BREACHED</td>
                                    {getSlaMatrixRows(config.slaDurations).map(row => (
                                        <td key={row.priority} className="border px-2 py-1 bg-red-50 text-red-900">
                                            <input
                                                type="number"
                                                className="w-20 border rounded p-1 text-xs bg-red-50"
                                                value={row.breached}
                                                readOnly
                                                tabIndex={-1}
                                            />
                                        </td>
                                    ))}
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div className="flex gap-2 mt-2">
                        <button
                            type="button"
                            className="text-xs text-blue-700 underline hover:text-blue-900"
                            onClick={handleResetSlaDurations}
                        >
                            Reset to Default
                        </button>
                        <span className="text-xs text-gray-400">Default: LOW/MEDIUM=240, HIGH/CRITICAL=120. WARNING = Initial - Threshold.</span>
                    </div>
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700">Plant Name</label>
                    <input
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 bg-gray-100"
                        value={config.plantName}
                        onChange={e => handleChange('plantName', e.target.value)}
                    />
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-gray-700">Show Stop Queue on Dashboard</span>
                    <button
                        className={`w-12 h-6 rounded-full p-1 transition-colors ${config.stopQueueVisible ? 'bg-blue-600' : 'bg-gray-300'}`}
                        onClick={() => handleChange('stopQueueVisible', !config.stopQueueVisible)}
                    >
                        <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform ${config.stopQueueVisible ? 'translate-x-6' : ''}`} />
                    </button>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700">Auto Logout (Minutes)</label>
                    <input
                        type="number"
                        min="1"
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                        value={config.autoLogoutMinutes}
                        onChange={e => handleChange('autoLogoutMinutes', e.target.value)}
                    />
                </div>

                <div className="border-t border-gray-100 pt-4 mt-4">
                    <h4 className="text-md font-semibold text-gray-700 mb-3 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                        WhatsApp Alerts
                    </h4>

                    {/* Worker Status Indicator */}
                    {(() => {
                        // Compute connection state once for reuse
                        let statusBadge = <span className="text-xs text-gray-400">Checking...</span>;
                        let isConnected = false;

                        if (config.whatsappHeartbeat) {
                            try {
                                const hb = typeof config.whatsappHeartbeat === 'string'
                                    ? JSON.parse(config.whatsappHeartbeat)
                                    : config.whatsappHeartbeat;

                                const now = Date.now();
                                const diff = (now - hb.ts) / 1000; // seconds
                                const stateUpper = (hb.state || '').toUpperCase();
                                const connectedStates = ['CONNECTED', 'PAIRED', 'AUTHENTICATED', 'READY'];

                                if (diff < 120) { // < 2 mins
                                    isConnected = connectedStates.includes(stateUpper);

                                    if (isConnected) {
                                        statusBadge = (
                                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                                <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                                                Online
                                            </span>
                                        );
                                    } else {
                                        statusBadge = (
                                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                                <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse"></span>
                                                {hb.state || "Connecting..."}
                                            </span>
                                        );
                                    }
                                } else {
                                    statusBadge = (
                                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                                            <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                                            Offline
                                        </span>
                                    );
                                }
                            } catch (e) {
                                console.error("Pulse error", e);
                            }
                        } else {
                            statusBadge = (
                                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                                    <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
                                    Unknown
                                </span>
                            );
                        }

                        return (
                            <div className="bg-gray-50 p-3 rounded-md mb-4 border border-gray-200">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-medium text-gray-500">Worker Status</span>
                                    {statusBadge}
                                </div>
                                <div className="flex items-center justify-between mt-2">
                                    <p className="text-[10px] text-gray-400 italic">
                                        Auto-refreshes every 15s. If "Offline", check Docker logs.
                                    </p>
                                    <button
                                        onClick={handleLogout}
                                        disabled={!isConnected}
                                        className={`text-[10px] font-bold px-2 py-1 rounded ${isConnected
                                            ? 'text-red-600 hover:text-red-800 hover:underline cursor-pointer'
                                            : 'text-gray-400 cursor-not-allowed'
                                            }`}
                                        title={isConnected ? "Logs out of WhatsApp session and clears local cache" : "No active session to logout"}
                                    >
                                        🚪 Logout Session
                                    </button>
                                </div>
                                {/* Show QR Code Button when not connected */}
                                {config.whatsappQRCode && (
                                    <button
                                        onClick={() => setShowQRModal(true)}
                                        className="mt-2 w-full px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
                                    >
                                        📱 Show QR Code to Connect
                                    </button>
                                )}
                            </div>
                        );
                    })()}

                    {/* QR Code Modal */}
                    {showQRModal && config.whatsappQRCode && (
                        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
                                <h3 className="text-lg font-semibold text-gray-800 mb-2">Scan QR Code</h3>
                                <p className="text-xs text-gray-500 mb-4">Open WhatsApp on your phone → Settings → Linked Devices → Link a Device → Scan this code.</p>
                                <div className="bg-white p-6 rounded border flex justify-center">
                                    <QRCode
                                        value={typeof config.whatsappQRCode === 'string' ? config.whatsappQRCode : JSON.stringify(config.whatsappQRCode)}
                                        size={280}
                                        level="M"
                                    />
                                </div>
                                <button
                                    onClick={() => { setShowQRModal(false); loadConfig(); }}
                                    className="mt-4 w-full px-4 py-2 text-sm font-medium text-white bg-gray-800 rounded-md hover:bg-gray-700"
                                >
                                    Close & Refresh Status
                                </button>
                            </div>
                        </div>
                    )}

                    <div className="flex items-center justify-between mb-4">
                        <span className="text-gray-700 text-sm">Enable WhatsApp for All Tickets</span>
                        <button
                            className={`w-12 h-6 rounded-full p-1 transition-colors ${config.whatsappEnabled ? 'bg-green-600' : 'bg-gray-300'}`}
                            onClick={() => handleChange('whatsappEnabled', !config.whatsappEnabled)}
                        >
                            <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform ${config.whatsappEnabled ? 'translate-x-6' : ''}`} />
                        </button>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">WhatsApp Alert Targets</label>
                        <input
                            type="text"
                            placeholder="e.g. P01, Escalation:BREACHED, +919876543210"
                            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                            value={config.whatsappTargetPhone}
                            onChange={e => handleChange('whatsappTargetPhone', e.target.value)}
                        />
                        <p className="text-[10px] text-gray-400 mt-1 italic">
                            <strong>Format:</strong> Comma-separated. Use <code>GroupName</code> for all alerts, or <code>GroupName:STATE</code> for conditional routing.<br />
                            <strong>States:</strong> <code>OK</code> (on-time), <code>WARNING</code> (near SLA), <code>BREACHED</code> (overdue).<br />
                            <strong>Example:</strong> <code>General:OK, Supervisors:WARNING, Escalation:BREACHED</code>
                        </p>
                    </div>

                    <div className="mt-6 border-t border-gray-100 pt-4">
                        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
                            <h6 className="text-xs font-bold text-blue-900 uppercase tracking-wide mb-3 flex items-center gap-2">
                                📋 Template Variable Reference
                            </h6>

                            <div className="space-y-3">
                                {/* Core Variables */}
                                <div>
                                    <p className="text-[10px] font-semibold text-blue-800 mb-1">Core (All Templates)</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {['{ticket_code}', '{asset_id}', '{title}', '{priority}', '{site_code}'].map(v => (
                                            <code key={v} className="px-1.5 py-0.5 bg-white text-blue-700 text-[10px] rounded border border-blue-200">{v}</code>
                                        ))}
                                    </div>
                                </div>

                                {/* Time Variables */}
                                <div>
                                    <p className="text-[10px] font-semibold text-amber-800 mb-1">Timing</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {['{created_at}', '{sla_due}'].map(v => (
                                            <code key={v} className="px-1.5 py-0.5 bg-white text-amber-700 text-[10px] rounded border border-amber-200">{v}</code>
                                        ))}
                                    </div>
                                </div>

                                {/* Assignment Variables */}
                                <div>
                                    <p className="text-[10px] font-semibold text-green-800 mb-1">Assignment</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {['{dept}', '{assigned_to}'].map(v => (
                                            <code key={v} className="px-1.5 py-0.5 bg-white text-green-700 text-[10px] rounded border border-green-200">{v}</code>
                                        ))}
                                    </div>
                                </div>

                                {/* Close-only Variables */}
                                <div>
                                    <p className="text-[10px] font-semibold text-purple-800 mb-1">Close Template Only</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {['{close_note}', '{resolution_reason}', '{closed_at}'].map(v => (
                                            <code key={v} className="px-1.5 py-0.5 bg-white text-purple-700 text-[10px] rounded border border-purple-200">{v}</code>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <p className="text-[9px] text-gray-500 mt-3 italic">
                                💡 Tip: <code className="bg-gray-100 px-1 rounded">{'{ticket_code}'}</code> = friendly ID like <code className="bg-gray-100 px-1 rounded">20260127-1030-0001</code>
                            </p>
                        </div>
                    </div>

                    <div className="mt-6 border-t border-gray-100 pt-4">
                        <h5 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Simulation & Testing 🧪</h5>

                        <div className="bg-blue-50 border border-blue-100 rounded-md p-3 mb-3">
                            <h6 className="text-xs font-semibold text-blue-800 mb-2">Step 1: Start a Test Scenario</h6>
                            <button
                                onClick={() => handleSimulate('stop')}
                                disabled={saving}
                                className="w-full px-3 py-2 text-xs font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
                            >
                                🚨 Create Test Ticket (Simulate Stop)
                            </button>
                            <p className="text-[10px] text-blue-600 mt-1.5 leading-tight">
                                Creates a new ticket in the "OPEN" state. This triggers the initial "Ticket Created" alert to the OK group.
                            </p>
                        </div>

                        <div className="bg-amber-50 border border-amber-100 rounded-md p-3">
                            <h6 className="text-xs font-semibold text-amber-800 mb-2">Step 2: Force Escalation (Time Travel)</h6>
                            <p className="text-[10px] text-amber-600 mb-2 leading-tight">
                                Manipulates the SLA time of the most recent OPEN ticket to force an alert state.
                            </p>
                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={() => handleSimulate('warning')}
                                    disabled={saving}
                                    className="px-3 py-2 text-xs font-medium text-amber-700 bg-white border border-amber-200 rounded-md hover:bg-amber-50 transition-colors flex items-center justify-center gap-2"
                                >
                                    ⚠️ Force Warning
                                </button>
                                <button
                                    onClick={() => handleSimulate('breach')}
                                    disabled={saving}
                                    className="px-3 py-2 text-xs font-medium text-red-700 bg-white border border-red-200 rounded-md hover:bg-red-50 transition-colors flex items-center justify-center gap-2"
                                >
                                    🔥 Force Breach
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700">Message Template (Ticket Created)</label>
                        <p className="text-[10px] text-gray-400 mb-1">
                            Sent to <code>OK</code> groups when a new ticket is created.
                        </p>
                        <textarea
                            className="w-full border border-gray-300 rounded-md shadow-sm p-2 text-sm font-mono h-24"
                            value={config.whatsappMessageTemplate || ''}
                            onChange={e => handleChange('whatsappMessageTemplate', e.target.value)}
                            placeholder="🚀 AssetIQ Ticket Created..."
                        />
                        <button
                            onClick={() => handleChange('whatsappMessageTemplate', "🚀 AssetIQ Ticket Created\nID: {ticket_code}\nAsset: {asset_id}\nTitle: {title}\nPriority: {priority}")}
                            className="text-[10px] text-purple-600 hover:text-purple-800 underline mt-1"
                        >
                            Reset to Default
                        </button>
                    </div>

                    <div className="mt-4 border-t border-dashed border-gray-200 pt-4">
                        <label className="block text-sm font-medium text-gray-700">Warning Template (SLA Approaching)</label>
                        <p className="text-[10px] text-gray-400 mb-1">
                            Sent to <code>WARNING</code> groups when ticket is near SLA deadline.
                        </p>
                        <textarea
                            className="w-full border border-gray-300 rounded-md shadow-sm p-2 text-sm font-mono h-24"
                            value={config.whatsappWarningMessageTemplate || ''}
                            onChange={e => handleChange('whatsappWarningMessageTemplate', e.target.value)}
                            placeholder={"⚠️ SLA Warning\nTicket: {ticket_code}\nAsset: {asset_id}..."}
                        />
                        <button
                            onClick={() => handleChange('whatsappWarningMessageTemplate', "⚠️ SLA Warning\nTicket: {ticket_code}\nAsset: {asset_id}\nTitle: {title}\nPriority: {priority}\nDue: {sla_due}")}
                            className="text-[10px] text-purple-600 hover:text-purple-800 underline mt-1"
                        >
                            Reset to Default
                        </button>
                    </div>

                    <div className="mt-4 border-t border-dashed border-gray-200 pt-4">
                        <label className="block text-sm font-medium text-gray-700">Breach Template (SLA Overdue)</label>
                        <p className="text-[10px] text-gray-400 mb-1">
                            Sent to <code>BREACHED</code> groups when ticket exceeds SLA deadline.
                        </p>
                        <textarea
                            className="w-full border border-gray-300 rounded-md shadow-sm p-2 text-sm font-mono h-24"
                            value={config.whatsappBreachMessageTemplate || ''}
                            onChange={e => handleChange('whatsappBreachMessageTemplate', e.target.value)}
                            placeholder={"🔥 SLA BREACHED\nTicket: {ticket_code}\nAsset: {asset_id}..."}
                        />
                        <button
                            onClick={() => handleChange('whatsappBreachMessageTemplate', "🔥 SLA BREACHED\nTicket: {ticket_code}\nAsset: {asset_id}\nTitle: {title}\nPriority: {priority}\nDue: {sla_due}")}
                            className="text-[10px] text-purple-600 hover:text-purple-800 underline mt-1"
                        >
                            Reset to Default
                        </button>
                    </div>

                    <div className="mt-4 border-t border-dashed border-gray-200 pt-4">
                        <label className="block text-sm font-medium text-gray-700">Closed Template (Ticket Resolved)</label>
                        <p className="text-[10px] text-gray-400 mb-1">
                            Sent when ticket is closed. Extra variables: <code>{'{close_note}'}</code>, <code>{'{resolution_reason}'}</code>, <code>{'{closed_at}'}</code>
                        </p>
                        <textarea
                            className="w-full border border-gray-300 rounded-md shadow-sm p-2 text-sm font-mono h-24"
                            value={config.whatsappCloseMessageTemplate || ''}
                            onChange={e => handleChange('whatsappCloseMessageTemplate', e.target.value)}
                            placeholder="✅ Ticket Closed..."
                        />
                        <button
                            onClick={() => handleChange('whatsappCloseMessageTemplate', "✅ Ticket Closed\nID: {ticket_code}\nTitle: {title}\nNote: {close_note}")}
                            className="text-[10px] text-purple-600 hover:text-purple-800 underline mt-1"
                        >
                            Reset to Default
                        </button>
                    </div>
                </div>

                <button
                    onClick={handleSave}
                    disabled={saving}
                    className={`bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 w-full mt-4 transition-opacity ${saving ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    {saving ? "Saving..." : "Save Configuration"}
                </button>

                {msg && (
                    <div className={`mt-4 text-center text-sm font-medium ${msg.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>
                        {msg}
                    </div>
                )}
            </div>
        </div>
    );
}

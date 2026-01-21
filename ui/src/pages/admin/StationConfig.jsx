import { useEffect, useState } from "react";
import QRCode from "react-qr-code";
import { apiGet, apiPost } from "../../api";

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
        whatsappQRCode: null
    });

    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState("");
    const [showQRModal, setShowQRModal] = useState(false);

    useEffect(() => {
        loadConfig();
    }, []);

    async function loadConfig() {
        try {
            const data = await apiGet("/master/config");
            setConfig(prev => ({ ...prev, ...data }));
        } catch (e) {
            console.error("Failed to load config", e);
        }
    }

    function handleChange(field, val) {
        setConfig({ ...config, [field]: val });
        setMsg("");
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

        try {
            await apiPost("/master/config", {
                stopQueueVisible: config.stopQueueVisible,
                autoLogoutMinutes: minutes,
                whatsappEnabled: config.whatsappEnabled,
                whatsappTargetPhone: config.whatsappTargetPhone,
                whatsappMessageTemplate: config.whatsappMessageTemplate,
                whatsappCloseMessageTemplate: config.whatsappCloseMessageTemplate
            });
            setMsg("Configuration saved successfully!");
            // Refresh global config if needed
            window.dispatchEvent(new Event("config:updated"));
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
                <div>
                    <label className="block text-sm font-medium text-gray-700">Plant Name</label>
                    <input
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 bg-gray-100"
                        value={config.plantName}
                        readOnly
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
                    <div className="bg-gray-50 p-3 rounded-md mb-4 border border-gray-200">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-gray-500">Worker Status</span>
                            {(() => {
                                let statusFn = () => <span className="text-xs text-gray-400">Checking...</span>;
                                if (config.whatsappHeartbeat) {
                                    try {
                                        const hb = typeof config.whatsappHeartbeat === 'string' 
                                            ? JSON.parse(config.whatsappHeartbeat) 
                                            : config.whatsappHeartbeat;
                                        
                                        const now = Date.now();
                                        const diff = (now - hb.ts) / 1000; // seconds
                                        
                                        if (diff < 120) { // < 2 mins
                                            if (hb.state === 'CONNECTED') {
                                                statusFn = () => (
                                                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                                                        Online
                                                    </span>
                                                );
                                            } else {
                                                statusFn = () => (
                                                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse"></span>
                                                        {hb.state || "Connecting..."}
                                                    </span>
                                                );
                                            }
                                        } else {
                                             statusFn = () => (
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
                                     statusFn = () => (
                                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                                            <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
                                            Unknown
                                        </span>
                                    );
                                }
                                return statusFn();
                            })()}
                        </div>
                         <p className="text-[10px] text-gray-400 mt-1">
                            Checks connectivity every 30s. If "Offline" or "DISCONNECTED", check Docker logs.
                        </p>
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
                            <strong>Format:</strong> Comma-separated. Use <code>GroupName</code> for all alerts, or <code>GroupName:STATE</code> for conditional routing.<br/>
                            <strong>States:</strong> <code>OK</code> (on-time), <code>WARNING</code> (near SLA), <code>BREACHED</code> (overdue).<br/>
                            <strong>Example:</strong> <code>General:OK, Supervisors:WARNING, Escalation:BREACHED</code>
                        </p>
                    </div>

                    <div className="mt-4">
                        <label className="block text-sm font-medium text-gray-700">Message Template</label>
                        <p className="text-[10px] text-gray-400 mb-1">
                            Supported: <code>{'{id}'}, {'{asset_id}'}, {'{title}'}, {'{priority}'}, {'{created_at}'}, {'{source}'}, {'{dept}'}, {'{assigned_to}'}, {'{sla_due}'}, {'{site_code}'}</code>
                        </p>
                        <textarea
                            className="w-full border border-gray-300 rounded-md shadow-sm p-2 text-sm font-mono h-24"
                            value={config.whatsappMessageTemplate || ''}
                            onChange={e => handleChange('whatsappMessageTemplate', e.target.value)}
                            placeholder="🚀 AssetIQ Ticket Created..."
                        />
                        <button 
                            onClick={() => handleChange('whatsappMessageTemplate', "🚀 AssetIQ Ticket Created\nID: {id}\nAsset: {asset_id}\nTitle: {title}\nPriority: {priority}")}
                            className="text-[10px] text-purple-600 hover:text-purple-800 underline mt-1"
                        >
                            Reset to Default
                        </button>
                    </div>

                    <div className="mt-4 border-t border-dashed border-gray-200 pt-4">
                        <label className="block text-sm font-medium text-gray-700">Closed Ticket Template</label>
                        <p className="text-[10px] text-gray-400 mb-1">
                            Supported: <code>{'{id}'}, {'{close_note}'}, {'{resolution_reason}'}, {'{closed_at}'}</code> + common fields
                        </p>
                        <textarea
                            className="w-full border border-gray-300 rounded-md shadow-sm p-2 text-sm font-mono h-24"
                            value={config.whatsappCloseMessageTemplate || ''}
                            onChange={e => handleChange('whatsappCloseMessageTemplate', e.target.value)}
                            placeholder="✅ Ticket Closed..."
                        />
                        <button 
                            onClick={() => handleChange('whatsappCloseMessageTemplate', "✅ Ticket Closed\nID: {id}\nNote: {close_note}")}
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

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../api";

export default function StationConfig() {
    const [config, setConfig] = useState({
        plantName: "Loading...",
        stopQueueVisible: true,
        autoLogoutMinutes: 30,
        whatsappEnabled: false,
        whatsappTargetPhone: "",
        whatsappMessageTemplate: "",
        whatsappCloseMessageTemplate: ""
    });

    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState("");

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
                        <label className="block text-sm font-medium text-gray-700">WhatsApp Alert Target (Phone or Group Name)</label>
                        <input
                            type="text"
                            placeholder="e.g. +919876543210 or 'AssetIQ Alerts'"
                            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                            value={config.whatsappTargetPhone}
                            onChange={e => handleChange('whatsappTargetPhone', e.target.value)}
                        />
                        <p className="text-[10px] text-gray-400 mt-1 italic">
                            Enter a full phone number with country code, or the <strong>exact name</strong> of a WhatsApp group.
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

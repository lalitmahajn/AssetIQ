import React, { useState, useEffect } from "react";
import { apiGet } from "../../api";

export default function StationConfig() {
    const [config, setConfig] = useState({
        plantName: "Loading...",
        enableWhatsApp: false,
        stopQueueVisible: true,
        autoLogoutMinutes: 30
    });

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
    }

    function handleSave() {
        alert("This configuration is currently managed via environmental variables (docker-compose). UI editing coming in Batch 10.");
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
                    <span className="text-gray-700">Enable WhatsApp Alerts</span>
                    <button
                        className={`w-12 h-6 rounded-full p-1 transition-colors ${config.enableWhatsApp ? 'bg-green-500' : 'bg-gray-300'}`}
                        onClick={() => handleChange('enableWhatsApp', !config.enableWhatsApp)}
                    >
                        <div className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform ${config.enableWhatsApp ? 'translate-x-6' : ''}`} />
                    </button>
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
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                        value={config.autoLogoutMinutes}
                        onChange={e => handleChange('autoLogoutMinutes', e.target.value)}
                    />
                </div>

                <button
                    onClick={handleSave}
                    className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 w-full mt-4"
                >
                    Save Configuration
                </button>
            </div>
        </div>
    );
}

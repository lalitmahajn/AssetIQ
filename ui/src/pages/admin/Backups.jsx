import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../api";

// Inline Icons to avoid extra dependencies
const DownloadIcon = ({ className }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
    </svg>
);

const HardDriveIcon = ({ className }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <line x1="22" y1="12" x2="2" y2="12"></line>
        <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path>
        <line x1="6" y1="16" x2="6.01" y2="16"></line>
        <line x1="10" y1="16" x2="10.01" y2="16"></line>
    </svg>
);

const RefreshIcon = ({ className }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path>
        <path d="M21 3v5h-5"></path>
        <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path>
        <path d="M8 16H3v5"></path>
    </svg>
);

export default function Backups() {
    const [backups, setBackups] = useState([]);
    const [loading, setLoading] = useState(false);
    const [triggering, setTriggering] = useState(false);
    const [msg, setMsg] = useState("");

    const BACKUP_RETENTION_DAYS = 0; // Fixed display as configured in .env (0=Infinite)

    useEffect(() => {
        loadBackups();
    }, []);

    async function loadBackups() {
        setLoading(true);
        try {
            const data = await apiGet("/backups/list");
            setBackups(data || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }

    async function handleTrigger() {
        if (!window.confirm("Trigger immediate backup? This might take a few seconds.")) return;
        setTriggering(true);
        setMsg("");
        try {
            const res = await apiPost("/backups/trigger", {});
            setMsg("✅ Backup triggered successfully! Refreshing list...");
            setTimeout(loadBackups, 2000); // Wait for FS write
        } catch (e) {
            setMsg("❌ Error: " + String(e));
        } finally {
            setTriggering(false);
        }
    }

    async function handleDownload(filename) {
        try {
            const token = localStorage.getItem("token");
            const res = await fetch(`${import.meta.env.VITE_API_BASE}/backups/download/${filename}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Download failed");

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (e) {
            alert("Download failed: " + e.message);
        }
    }

    return (
        <div className="max-w-5xl mx-auto p-4">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                        <HardDriveIcon className="h-6 w-6 text-blue-600" />
                        Database Backups
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                        Secure snapshots of your entire system. Stored indefinitely.
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={loadBackups}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-full"
                        title="Refresh List"
                    >
                        <RefreshIcon className={`h-5 w-5 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <button
                        onClick={handleTrigger}
                        disabled={triggering}
                        className={`px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors flex items-center gap-2 ${triggering ? "opacity-50 cursor-not-allowed" : ""}`}
                    >
                        {triggering ? "Backing up..." : "+ Create Backup Now"}
                    </button>
                </div>
            </div>

            {msg && (
                <div className={`mb-4 p-3 rounded text-sm font-medium ${msg.startsWith("✅") ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
                    {msg}
                </div>
            )}

            <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-4 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
                    <span className="text-xs font-bold uppercase text-gray-500 tracking-wider">
                        {backups.length} Snapshots Available
                    </span>
                    <span className="text-xs text-gray-400">
                        Path: <code>/data/report_vault/backups/</code>
                    </span>
                </div>

                {backups.length === 0 && !loading ? (
                    <div className="p-12 text-center text-gray-400">
                        <HardDriveIcon className="h-12 w-12 mx-auto mb-3 opacity-20" />
                        <p>No backups found.</p>
                        <p className="text-xs mt-1">Check if the "Maintenance Agent" is running.</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {backups.map(b => (
                            <div key={b.filename} className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className="h-10 w-10 bg-blue-50 rounded-lg flex items-center justify-center text-blue-600">
                                        <span className="font-mono text-xs font-bold">SQL</span>
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-medium text-gray-900">{b.filename}</h4>
                                        <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5">
                                            <span>📅 {b.created_at_fmt}</span>
                                            <span>💾 {b.size_mb} MB</span>
                                        </div>
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleDownload(b.filename)}
                                    className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-all"
                                    title="Download Backup"
                                >
                                    <DownloadIcon className="h-5 w-5" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

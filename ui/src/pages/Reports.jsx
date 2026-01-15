import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";

function isoToday() {
    return new Date().toISOString().split('T')[0];
}

export default function Reports() {
    const [reportType, setReportType] = useState("daily_summary");
    const [dateFrom, setDateFrom] = useState(isoToday());
    const [dateTo, setDateTo] = useState(isoToday());

    const [requests, setRequests] = useState([]);
    const [vaultFiles, setVaultFiles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState("");

    async function load() {
        setLoading(true);
        try {
            const [reqs, vault] = await Promise.all([
                apiGet("/reports/list-requests"),
                apiGet("/reports/list-vault")
            ]);
            setRequests(reqs || []);
            setVaultFiles(vault.items || []);
        } catch (e) {
            setErr(e.message);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        load();
    }, []);

    async function handleGenerate() {
        setErr("");
        setLoading(true);
        try {
            await apiPost("/reports/request", {
                report_type: reportType,
                date_from: dateFrom,
                date_to: dateTo
            });
            await load();
        } catch (e) {
            setErr(e.message);
        } finally {
            setLoading(false);
        }
    }

    async function download(r) {
        try {
            // Get token
            const res = await apiPost("/reports/issue-download", {
                rel_path: r.rel_path,
                report_request_id: r.id
            });
            if (res.token) {
                const url = `${import.meta.env.VITE_API_BASE}/reports/download?token=${res.token}`;
                window.open(url, "_blank");
            }
        } catch (e) {
            alert("Failed to download: " + e.message);
        }
    }

    return (
        <div className="max-w-6xl mx-auto py-6 space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Reporting System</h2>
                    <p className="text-gray-500 text-sm mt-1">Generate and access historical downtime and summary reports.</p>
                </div>
                <button onClick={load} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                </button>
            </div>

            {err && <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-xl text-sm">{err}</div>}

            {/* Manual Trigger Section */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
                    <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" /></svg>
                    Generate Custom Report
                </h3>
                <div className="grid md:grid-cols-4 gap-6 items-end">
                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Report Type</label>
                        <select
                            value={reportType}
                            onChange={e => setReportType(e.target.value)}
                            className="w-full h-11 bg-gray-50 border border-gray-200 rounded-xl px-4 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                        >
                            <option value="daily_summary">Daily Summary</option>
                            <option value="downtime_by_asset">Downtime by Asset</option>
                        </select>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Date From</label>
                        <input
                            type="date"
                            value={dateFrom}
                            onChange={e => setDateFrom(e.target.value)}
                            className="w-full h-11 bg-gray-50 border border-gray-200 rounded-xl px-4 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Date To</label>
                        <input
                            type="date"
                            value={dateTo}
                            onChange={e => setDateTo(e.target.value)}
                            className="w-full h-11 bg-gray-50 border border-gray-200 rounded-xl px-4 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    <button
                        onClick={handleGenerate}
                        disabled={loading}
                        className="h-11 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-xl font-bold text-sm shadow-lg shadow-blue-200 transition-all flex items-center justify-center gap-2"
                    >
                        {loading ? "Processing..." : "Generate Report"}
                    </button>
                </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-8">
                {/* Recent Requests */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden h-fit">
                    <div className="p-5 border-b border-gray-100 bg-gray-50">
                        <h4 className="font-bold text-gray-700">Request Queue</h4>
                    </div>
                    <div className="divide-y divide-gray-100 max-h-[400px] overflow-y-auto">
                        {requests.map(r => (
                            <div key={r.id} className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                                <div>
                                    <div className="text-sm font-bold text-gray-800 uppercase tabular-nums">#{r.id} - {r.report_type.replace(/_/g, ' ')}</div>
                                    <div className="text-xs text-gray-400 mt-0.5">{r.date_from} to {r.date_to}</div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${r.status === 'generated' ? 'bg-green-100 text-green-700' :
                                            r.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700 animate-pulse'
                                        }`}>
                                        {r.status}
                                    </span>
                                    {r.status === 'generated' && (
                                        <button onClick={() => download(r)} className="text-blue-600 hover:text-blue-800">
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                        {requests.length === 0 && <div className="p-12 text-center text-gray-400 italic">No recent requests.</div>}
                    </div>
                </div>

                {/* Vault Files */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden h-fit">
                    <div className="p-5 border-b border-gray-100 bg-gray-50">
                        <h4 className="font-bold text-gray-700">Report Vault</h4>
                    </div>
                    <div className="divide-y divide-gray-100 max-h-[400px] overflow-y-auto">
                        {vaultFiles.map((f, i) => (
                            <div key={i} className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-[10px] ${f.type === 'PDF' ? 'bg-red-50 text-red-500' : 'bg-green-50 text-green-500'
                                        }`}>
                                        {f.type}
                                    </div>
                                    <div>
                                        <div className="text-sm font-bold text-gray-800 truncate max-w-[180px]">{f.name}</div>
                                        <div className="text-xs text-gray-400 mt-0.5">{(f.size / 1024).toFixed(1)} KB • {new Date(f.mtime * 1000).toLocaleDateString()}</div>
                                    </div>
                                </div>
                                <button onClick={() => download(f)} className="text-blue-600 hover:text-blue-800">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                                </button>
                            </div>
                        ))}
                        {vaultFiles.length === 0 && <div className="p-12 text-center text-gray-400 italic">Vault is empty.</div>}
                    </div>
                </div>
            </div>
        </div>
    );
}

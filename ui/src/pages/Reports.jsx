import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";

function isoToday() {
    return new Date().toISOString().split('T')[0];
}

export default function Reports() {
    const [reportType, setReportType] = useState("daily_summary");
    const [dateFrom, setDateFrom] = useState(isoToday());
    const [dateTo, setDateTo] = useState(isoToday());
    const [timeFrom, setTimeFrom] = useState("00:00");
    const [timeTo, setTimeTo] = useState("23:59");

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
            // Combine date and time into ISO datetime strings
            const fromDateTime = `${dateFrom}T${timeFrom}:00`;
            const toDateTime = `${dateTo}T${timeTo}:00`;

            await apiPost("/reports/request", {
                report_type: reportType,
                date_from: fromDateTime,
                date_to: toDateTime
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
                <div className="grid md:grid-cols-6 gap-4 items-end">
                    <div className="space-y-1.5 md:col-span-2">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Report Type</label>
                        <select
                            value={reportType}
                            onChange={e => setReportType(e.target.value)}
                            className="w-full h-11 bg-gray-50 border border-gray-200 rounded-xl px-4 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                        >
                            <option value="daily_summary">Summary Report</option>
                            <option value="downtime_by_asset">Downtime by Asset</option>
                        </select>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">From Date</label>
                        <input
                            type="date"
                            value={dateFrom}
                            onChange={e => setDateFrom(e.target.value)}
                            className="w-full h-11 bg-gray-50 border border-gray-200 rounded-xl px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">From Time</label>
                        <input
                            type="time"
                            value={timeFrom}
                            onChange={e => setTimeFrom(e.target.value)}
                            className="w-full h-11 bg-gray-50 border border-gray-200 rounded-xl px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">To Date</label>
                        <input
                            type="date"
                            value={dateTo}
                            onChange={e => setDateTo(e.target.value)}
                            className="w-full h-11 bg-gray-50 border border-gray-200 rounded-xl px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">To Time</label>
                        <input
                            type="time"
                            value={timeTo}
                            onChange={e => setTimeTo(e.target.value)}
                            className="w-full h-11 bg-gray-50 border border-gray-200 rounded-xl px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                </div>
                <div className="mt-6 flex items-center gap-4">
                    <button
                        onClick={handleGenerate}
                        disabled={loading}
                        className="h-11 px-8 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-xl font-bold text-sm shadow-lg shadow-blue-200 transition-all flex items-center justify-center gap-2"
                    >
                        {loading && (
                            <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                        )}
                        {loading ? "Generating Report..." : "Generate Report"}
                    </button>
                    {loading && (
                        <span className="text-sm font-medium text-blue-600 animate-pulse flex items-center gap-2">
                            Processing... Please wait
                        </span>
                    )}
                </div>
            </div>

            <div className="max-w-4xl">
                {/* Report Vault */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden h-fit">
                    <div className="p-5 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
                        <h4 className="font-bold text-gray-700">Report Vault</h4>
                        <span className="text-xs text-gray-400 uppercase font-bold tracking-widest">{vaultFiles.length} Files</span>
                    </div>
                    <div className="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
                        {vaultFiles.map((f, i) => (
                            <div key={i} className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-[10px] ${f.type === 'PDF' ? 'bg-red-50 text-red-500' : 'bg-green-50 text-green-500'
                                        }`}>
                                        {f.type}
                                    </div>
                                    <div>
                                        <div className="text-sm font-bold text-gray-800 truncate max-w-[400px]">{f.name}</div>
                                        <div className="text-xs text-gray-400 mt-0.5">{(f.size / 1024).toFixed(1)} KB • {new Date(f.mtime * 1000).toLocaleString()}</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button onClick={() => download(f)} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg group transition-all" title="Download">
                                        <svg className="w-5 h-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                                    </button>
                                </div>
                            </div>
                        ))}
                        {vaultFiles.length === 0 && <div className="p-12 text-center text-gray-400 italic font-medium">No reports generated yet.</div>}
                    </div>
                </div>
            </div>
        </div>
    );
}

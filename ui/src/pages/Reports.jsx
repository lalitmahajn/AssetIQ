import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";

function isoToday() {
    return new Date().toISOString().split('T')[0];
}

// Report type definitions with metadata
const REPORT_TYPES = [
    { value: "daily_summary", label: "Summary Report", description: "Executive overview with KPIs, downtime, and ticket metrics", format: "PDF", category: "Summary" },
    { value: "ticket_performance", label: "Ticket Performance", description: "SLA compliance, MTTR, ticket distribution by priority/status/department", format: "PDF", category: "Summary" },
    { value: "stop_reason_analysis", label: "Stop Reason Analysis", description: "Pareto analysis of stop reasons by frequency and downtime", format: "PDF", category: "Summary" },
    { value: "critical_asset", label: "Critical Asset Report", description: "Focus on critical assets: stops, downtime, and open tickets", format: "PDF", category: "Summary" },
    { value: "trend_analysis", label: "Trend Analysis", description: "Daily trends of stops, tickets, and downtime over time", format: "PDF", category: "Summary" },
    { value: "downtime_by_asset", label: "Downtime by Asset", description: "Detailed stop records per asset with duration", format: "Excel", category: "Detailed" },
    { value: "sla_breach", label: "SLA Breach Report", description: "List of tickets that violated or are violating SLA", format: "Excel", category: "Detailed" },
    { value: "asset_health", label: "Asset Health Report", description: "Per-asset availability, stop count, and downtime metrics", format: "Excel", category: "Detailed" },
    { value: "personnel_performance", label: "Personnel Performance", description: "Maintenance technician metrics: tickets handled, resolution rates", format: "Excel", category: "Detailed" },
    { value: "department_performance", label: "Department Performance", description: "Department-level ticket metrics and SLA compliance", format: "Excel", category: "Detailed" },
    { value: "audit_trail", label: "Audit Trail", description: "Export of system audit logs with user actions", format: "Excel", category: "Admin" },
];

export default function Reports() {
    const [reportType, setReportType] = useState("daily_summary");
    const [dateFrom, setDateFrom] = useState(isoToday());
    const [dateTo, setDateTo] = useState(isoToday());
    const [timeFrom, setTimeFrom] = useState("00:00");
    const [timeTo, setTimeTo] = useState("23:59");

    // Dynamic filters
    const [filters, setFilters] = useState({});
    const [filterOptions, setFilterOptions] = useState({ assets: [], users: [], departments: [], entity_types: [] });

    const [requests, setRequests] = useState([]);
    const [vaultFiles, setVaultFiles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState("");
    const [lastGenerated, setLastGenerated] = useState(null); // Track last generated report for instant download

    async function loadFilterOptions() {
        try {
            const opts = await apiGet("/reports/filter-options");
            setFilterOptions(opts || { assets: [], users: [], departments: [], entity_types: [] });
        } catch (e) {
            console.error("Failed to load filter options:", e);
        }
    }

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
        loadFilterOptions();
    }, []);

    // Reset filters when report type changes
    useEffect(() => {
        setFilters({});
    }, [reportType]);

    const selectedReport = REPORT_TYPES.find(r => r.value === reportType);

    async function handleGenerate() {
        setErr("");
        setLoading(true);
        setLastGenerated(null);
        try {
            // Combine date and time into ISO datetime strings
            const fromDateTime = `${dateFrom}T${timeFrom}:00`;
            const toDateTime = `${dateTo}T${timeTo}:00`;

            const result = await apiPost("/reports/request", {
                report_type: reportType,
                date_from: fromDateTime,
                date_to: toDateTime,
                filters: filters
            });
            
            // Store the generated report info for instant download
            if (result && result.id) {
                setLastGenerated({ id: result.id, status: result.status });
            }
            
            // Refresh vault list
            await load();
        } catch (e) {
            setErr(e.message);
        } finally {
            setLoading(false);
        }
    }

    async function download(r, viewMode = false) {
        try {
            // Get token
            const res = await apiPost("/reports/issue-download", {
                rel_path: r.rel_path,
                report_request_id: r.id
            });
            if (res.token) {
                const url = `${import.meta.env.VITE_API_BASE}/reports/download?token=${res.token}${viewMode ? '&view=true' : ''}`;
                window.open(url, "_blank");
            }
        } catch (e) {
            alert("Failed to " + (viewMode ? "view" : "download") + ": " + e.message);
        }
    }

    async function downloadLastGenerated(viewMode = false) {
        if (!lastGenerated) return;
        try {
            const res = await apiPost("/reports/issue-download", {
                report_request_id: lastGenerated.id
            });
            if (res.token) {
                const url = `${import.meta.env.VITE_API_BASE}/reports/download?token=${res.token}${viewMode ? '&view=true' : ''}`;
                window.open(url, "_blank");
            }
        } catch (e) {
            alert("Failed to " + (viewMode ? "view" : "download") + ": " + e.message);
        }
    }

    // Render dynamic filter fields based on report type
    function renderFilters() {
        switch (reportType) {
            case "asset_health":
                return (
                    <div className="grid md:grid-cols-2 gap-4 mt-4 p-4 bg-gray-50 rounded-xl border border-gray-100">
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Filter by Asset</label>
                            <select
                                value={filters.asset_id || ""}
                                onChange={e => setFilters({ ...filters, asset_id: e.target.value || undefined })}
                                className="w-full h-10 bg-white border border-gray-200 rounded-lg px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="">All Assets</option>
                                {filterOptions.assets.map(a => (
                                    <option key={a.id} value={a.id}>{a.name || a.id}</option>
                                ))}
                            </select>
                        </div>
                        <div className="flex items-center gap-3 pt-6">
                            <input
                                type="checkbox"
                                id="critical_only"
                                checked={filters.critical_only || false}
                                onChange={e => setFilters({ ...filters, critical_only: e.target.checked })}
                                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                            />
                            <label htmlFor="critical_only" className="text-sm font-medium text-gray-700">Critical Assets Only</label>
                        </div>
                    </div>
                );

            case "personnel_performance":
                return (
                    <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-100">
                        <div className="space-y-1.5 max-w-xs">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Filter by User</label>
                            <select
                                value={filters.user_id || ""}
                                onChange={e => setFilters({ ...filters, user_id: e.target.value || undefined })}
                                className="w-full h-10 bg-white border border-gray-200 rounded-lg px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="">All Users</option>
                                {filterOptions.users.map(u => (
                                    <option key={u.id} value={u.id}>{u.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                );

            case "audit_trail":
                return (
                    <div className="grid md:grid-cols-2 gap-4 mt-4 p-4 bg-gray-50 rounded-xl border border-gray-100">
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Entity Type</label>
                            <select
                                value={filters.entity_type || ""}
                                onChange={e => setFilters({ ...filters, entity_type: e.target.value || undefined })}
                                className="w-full h-10 bg-white border border-gray-200 rounded-lg px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="">All Types</option>
                                {filterOptions.entity_types.map(t => (
                                    <option key={t} value={t}>{t.replace(/_/g, ' ').toUpperCase()}</option>
                                ))}
                            </select>
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Filter by User</label>
                            <select
                                value={filters.user_id || ""}
                                onChange={e => setFilters({ ...filters, user_id: e.target.value || undefined })}
                                className="w-full h-10 bg-white border border-gray-200 rounded-lg px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="">All Users</option>
                                {filterOptions.users.map(u => (
                                    <option key={u.id} value={u.id}>{u.name}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                );

            default:
                return null;
        }
    }

    // Group reports by category
    const categories = [...new Set(REPORT_TYPES.map(r => r.category))];

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
                            {categories.map(cat => (
                                <optgroup key={cat} label={`── ${cat} Reports ──`}>
                                    {REPORT_TYPES.filter(r => r.category === cat).map(r => (
                                        <option key={r.value} value={r.value}>
                                            {r.label} ({r.format})
                                        </option>
                                    ))}
                                </optgroup>
                            ))}
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

                {/* Report description */}
                {selectedReport && (
                    <div className="mt-4 flex items-center gap-3 p-3 bg-blue-50 rounded-xl border border-blue-100">
                        <div className={`px-2 py-1 rounded-md text-xs font-bold ${selectedReport.format === 'PDF' ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}`}>
                            {selectedReport.format}
                        </div>
                        <p className="text-sm text-blue-800">{selectedReport.description}</p>
                    </div>
                )}

                {/* Dynamic filters */}
                {renderFilters()}

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
                    
                    {/* View/Download buttons - only visible after report is generated */}
                    {lastGenerated && lastGenerated.status === "generated" && (
                        <>
                            <button
                                onClick={() => downloadLastGenerated(true)}
                                className="h-11 px-5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-bold text-sm shadow-lg shadow-purple-200 transition-all flex items-center justify-center gap-2"
                                title={selectedReport?.format === 'PDF' ? 'Open in browser' : 'Open with default app'}
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                                View
                            </button>
                            <button
                                onClick={() => downloadLastGenerated(false)}
                                className="h-11 px-5 bg-green-600 hover:bg-green-700 text-white rounded-xl font-bold text-sm shadow-lg shadow-green-200 transition-all flex items-center justify-center gap-2"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                Download
                            </button>
                        </>
                    )}
                    
                    {loading && (
                        <span className="text-sm font-medium text-blue-600 animate-pulse flex items-center gap-2">
                            Processing... Please wait
                        </span>
                    )}
                    
                    {lastGenerated && lastGenerated.status === "generated" && !loading && (
                        <span className="text-sm font-medium text-green-600 flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                            </svg>
                            Report Ready!
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
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-[10px] ${f.type === 'PDF' ? 'bg-red-50 text-red-500' : f.type === 'EXCEL' ? 'bg-green-50 text-green-500' : 'bg-blue-50 text-blue-500'
                                        }`}>
                                        {f.type}
                                    </div>
                                    <div>
                                        <div className="text-sm font-bold text-gray-800 truncate max-w-[400px]">{f.name}</div>
                                        <div className="text-xs text-gray-400 mt-0.5">{(f.size / 1024).toFixed(1)} KB • {new Date(f.mtime * 1000).toLocaleString()}</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-1">
                                    <button onClick={() => download(f, true)} className="p-2 text-purple-600 hover:bg-purple-50 rounded-lg group transition-all" title={f.type === 'PDF' ? 'Open in browser' : 'Open with default app'}>
                                        <svg className="w-5 h-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                                    </button>
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

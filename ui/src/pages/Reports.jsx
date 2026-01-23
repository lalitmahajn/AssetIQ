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
    const [customName, setCustomName] = useState("");
    const [showModal, setShowModal] = useState(false);
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
                custom_name: customName || undefined,
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
            setShowModal(false); // Close modal on success
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
            {/* Header Actions */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Reporting Vault</h2>
                    <p className="text-gray-500 text-sm mt-1">Access historical reports or generate new ones.</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={load} className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    </button>
                    <button
                        onClick={() => setShowModal(true)}
                        className="h-10 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-sm shadow-sm transition-all flex items-center gap-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>
                        New Report
                    </button>
                </div>
            </div>

            {err && <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-xl text-sm">{err}</div>}

            {/* Last Generated Banner */}
            {lastGenerated && lastGenerated.status === "generated" && (
                <div className="bg-green-50 border border-green-100 p-4 rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="bg-green-100 p-2 rounded-lg text-green-600">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        </div>
                        <div>
                            <h4 className="font-bold text-green-900">Report Ready!</h4>
                            <p className="text-green-700 text-xs">Your report has been generated successfully.</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => downloadLastGenerated(true)}
                            className="px-4 py-2 bg-white text-green-700 border border-green-200 hover:bg-green-50 rounded-lg font-bold text-sm transition-all"
                        >
                            View
                        </button>
                        <button
                            onClick={() => downloadLastGenerated(false)}
                            className="px-4 py-2 bg-green-600 text-white hover:bg-green-700 rounded-lg font-bold text-sm shadow-sm transition-all"
                        >
                            Download
                        </button>
                    </div>
                </div>
            )}

            {/* Generation Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
                        <div className="p-6 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
                            <div>
                                <h3 className="text-xl font-bold text-gray-900">Generate Report</h3>
                                <p className="text-sm text-gray-500">Configure parameters for your custom report</p>
                            </div>
                            <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                            </button>
                        </div>

                        <div className="p-6 space-y-6">
                            {/* Two Column Layout */}
                            <div className="grid md:grid-cols-2 gap-6">
                                {/* Left: Type & Name */}
                                <div className="space-y-4">
                                    <div className="space-y-1.5">
                                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Report Type</label>
                                        <select
                                            value={reportType}
                                            onChange={e => setReportType(e.target.value)}
                                            className="w-full h-11 bg-white border border-gray-200 rounded-xl px-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none shadow-sm"
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

                                    {/* Description Box */}
                                    {selectedReport && (
                                        <div className="p-3 bg-blue-50 rounded-xl border border-blue-100 text-sm text-blue-800 leading-relaxed">
                                            {selectedReport.description}
                                        </div>
                                    )}

                                    <div className="space-y-1.5">
                                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Custom Name (Optional)</label>
                                        <input
                                            type="text"
                                            value={customName}
                                            onChange={e => setCustomName(e.target.value)}
                                            placeholder="e.g. Shift_A_Review"
                                            className="w-full h-11 bg-white border border-gray-200 rounded-xl px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                                        />
                                        <p className="text-[10px] text-gray-400 text-right">Will be prefixed to filename</p>
                                    </div>
                                </div>

                                {/* Right: Date & Time */}
                                <div className="space-y-4 bg-gray-50 p-4 rounded-xl border border-gray-100">
                                    <h4 className="text-sm font-bold text-gray-700 border-b border-gray-200 pb-2 mb-2">Time Period</h4>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="space-y-1">
                                            <label className="text-[10px] font-bold text-gray-400 uppercase">From Date</label>
                                            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="w-full h-9 rounded-lg border-gray-200 text-sm" />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[10px] font-bold text-gray-400 uppercase">Time</label>
                                            <input type="time" value={timeFrom} onChange={e => setTimeFrom(e.target.value)} className="w-full h-9 rounded-lg border-gray-200 text-sm" />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[10px] font-bold text-gray-400 uppercase">To Date</label>
                                            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="w-full h-9 rounded-lg border-gray-200 text-sm" />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[10px] font-bold text-gray-400 uppercase">Time</label>
                                            <input type="time" value={timeTo} onChange={e => setTimeTo(e.target.value)} className="w-full h-9 rounded-lg border-gray-200 text-sm" />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Dynamic Filters */}
                            <div className="pt-2 border-t border-gray-100">
                                {renderFilters()}
                            </div>
                        </div>

                        <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
                            <button
                                onClick={() => setShowModal(false)}
                                className="px-5 py-2.5 text-gray-600 font-bold text-sm hover:bg-gray-200 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleGenerate}
                                disabled={loading}
                                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-sm shadow-lg shadow-blue-200 transition-all flex items-center gap-2 disabled:bg-gray-300 disabled:shadow-none"
                            >
                                {loading ? (
                                    <>
                                        <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                                        Generating...
                                    </>
                                ) : (
                                    "Generate"
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

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
        </div >
    );
}

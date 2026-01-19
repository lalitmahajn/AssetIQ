import { useEffect, useState } from "react";
import { apiGet } from "../../api";

const FormatDetails = ({ details }) => {
    if (!details) return <span className="text-gray-400 italic">No details</span>;
    
    let parsed = details;
    if (typeof details === 'string') {
        try {
            // Try to fix Python-style strings if they come back (single quotes)
            const jsonFriendly = details.replace(/'/g, '"');
            parsed = JSON.parse(jsonFriendly);
        } catch (e) {
            return <span className="text-gray-500 font-mono">{details}</span>;
        }
    }

    if (typeof parsed !== 'object' || parsed === null) {
        return <span className="text-gray-500 font-mono">{String(parsed)}</span>;
    }

    const entries = Object.entries(parsed);
    if (entries.length === 0) return <span className="text-gray-400 italic">Empty object</span>;

    return (
        <div className="flex flex-wrap gap-1.5 min-w-[200px]">
            {entries.map(([k, v]) => (
                <div key={k} className="flex items-center bg-gray-100/80 border border-gray-200 rounded px-1.5 py-0.5" title={`${k}: ${v}`}>
                    <span className="text-[9px] font-black text-gray-400 uppercase mr-1.5 tracking-tighter">{k}</span>
                    <span className="text-[10px] font-bold text-gray-700 truncate max-w-[100px]">{String(v)}</span>
                </div>
            ))}
        </div>
    );
};

export default function AuditLogViewer() {
    const [logs, setLogs] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [err, setErr] = useState("");
    const [offset, setOffset] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(50);

    async function load() {
        setLoading(true);
        try {
            const data = await apiGet(`/master/audit/list?limit=${rowsPerPage}&offset=${offset}`);
            setLogs(data.items || []);
            setTotal(data.total || 0);
        } catch (e) {
            setErr(String(e));
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { load(); }, [offset, rowsPerPage]);

    const handleRowsChange = (e) => {
        setRowsPerPage(parseInt(e.target.value));
        setOffset(0); // Reset to first page
    };

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white">
                <div>
                    <h3 className="text-xl font-bold text-gray-800">Audit Logs</h3>
                    <p className="text-xs text-gray-500 mt-1 uppercase tracking-wider font-semibold">Security & Activity History</p>
                </div>
                <button
                    onClick={load}
                    className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors shadow-sm"
                >
                    Refresh Logs
                </button>
            </div>

            {err && <div className="mx-6 mt-4 text-red-600 bg-red-50 p-3 rounded-lg border border-red-100 text-sm">{err}</div>}

            {/* MATERIAL-STYLE PAGINATION - TOP */}
            <div className="bg-white px-6 py-4 flex items-center justify-end text-sm text-gray-600 gap-8 border-b border-gray-100">
                <div className="flex items-center gap-3">
                    <span className="text-gray-500 text-xs font-medium">Rows per page:</span>
                    <select 
                        value={rowsPerPage} 
                        onChange={handleRowsChange}
                        className="bg-transparent border-none focus:ring-0 cursor-pointer font-bold text-gray-800 text-sm py-0"
                    >
                        <option value={10}>10</option>
                        <option value={25}>25</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                    </select>
                </div>

                <div className="font-medium text-xs tracking-tight">
                    {total > 0 ? `${offset + 1}–${Math.min(offset + rowsPerPage, total)} of ${total}` : '0-0 of 0'}
                </div>

                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setOffset(Math.max(0, offset - rowsPerPage))}
                        disabled={offset === 0 || loading}
                        className="p-1.5 rounded-full hover:bg-gray-200 disabled:opacity-30 transition-colors"
                        title="Previous page"
                    >
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                    </button>
                    <button
                        onClick={() => setOffset(offset + rowsPerPage)}
                        disabled={offset + rowsPerPage >= total || loading}
                        className="p-1.5 rounded-full hover:bg-gray-200 disabled:opacity-30 transition-colors"
                        title="Next page"
                    >
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" /></svg>
                    </button>
                </div>
            </div>

            <div className="overflow-x-auto min-h-[400px]">
                <table className="w-full text-left text-sm italic-last-col">
                    <thead>
                        <tr className="bg-gray-50/50 text-gray-500 uppercase text-[10px] font-bold tracking-widest border-b border-gray-100">
                            <th className="py-4 px-6">Timestamp (UTC)</th>
                            <th className="py-4 px-6">User / Actor</th>
                            <th className="py-4 px-6">Action</th>
                            <th className="py-4 px-6">Entity Involved</th>
                            <th className="py-4 px-6">Technical Details</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {loading ? (
                            <tr><td colSpan={5} className="py-20 text-center text-gray-400">
                                <div className="flex flex-col items-center gap-2">
                                    <div className="w-8 h-8 border-4 border-blue-100 border-t-blue-600 rounded-full animate-spin"></div>
                                    <span className="text-xs font-semibold tracking-wide">Fetching system logs...</span>
                                </div>
                            </td></tr>
                        ) : logs.length === 0 ? (
                            <tr><td colSpan={5} className="py-20 text-center text-gray-500 italic">No activity recorded for this period.</td></tr>
                        ) : logs.map(l => (
                            <tr key={l.id} className="hover:bg-blue-50/30 transition-colors group">
                                <td className="py-4 px-6 whitespace-nowrap text-gray-500 font-mono text-xs">
                                    {new Date(l.created_at_utc).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                                </td>
                                <td className="py-4 px-6">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ring-2 ring-white
                                            ${l.actor_user_id ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-700'}`}>
                                            {(l.actor_user_id || "S")[0].toUpperCase()}
                                        </div>
                                        <span className="font-bold text-gray-700 truncate max-w-[120px]">{l.actor_user_id || "SYSTEM"}</span>
                                    </div>
                                </td>
                                <td className="py-4 px-6">
                                    <span className={`px-2.5 py-1 rounded-md text-[10px] font-black uppercase tracking-tighter shadow-sm ${
                                        l.action.includes('DELETE') ? 'bg-red-50 text-red-700 border border-red-100' : 
                                        l.action.includes('CREATE') ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' :
                                        'bg-blue-50 text-blue-700 border border-blue-100'
                                    }`}>
                                        {l.action}
                                    </span>
                                </td>
                                <td className="py-4 px-6">
                                    <div className="flex flex-col">
                                        <span className="font-bold text-gray-800 text-xs">{l.entity_type}</span>
                                        <span className="text-[10px] text-gray-400 font-mono">#{l.entity_id}</span>
                                    </div>
                                </td>
                                <td className="py-4 px-6">
                                    <FormatDetails details={l.details} />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

import React, { useEffect, useState } from "react";
import { apiGet } from "../../api";

export default function AuditLogViewer() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [err, setErr] = useState("");

    async function load() {
        setLoading(true);
        try {
            const data = await apiGet("/master/audit/list?limit=50");
            setLogs(data);
        } catch (e) {
            setErr(String(e));
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { load(); }, []);

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-gray-800">Audit Logs</h3>
                <button
                    onClick={load}
                    className="bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300 text-sm"
                >
                    Refresh
                </button>
            </div>

            {err && <div className="text-red-600 mb-4 bg-red-50 p-2 rounded">{err}</div>}

            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead>
                        <tr className="border-b bg-gray-50">
                            <th className="py-2 px-3">Time (UTC)</th>
                            <th className="py-2 px-3">User</th>
                            <th className="py-2 px-3">Action</th>
                            <th className="py-2 px-3">Entity</th>
                            <th className="py-2 px-3">Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan={5} className="py-4 text-center">Loading...</td></tr>
                        ) : logs.length === 0 ? (
                            <tr><td colSpan={5} className="py-4 text-center text-gray-500">No logs found.</td></tr>
                        ) : logs.map(l => (
                            <tr key={l.id} className="border-b hover:bg-gray-50">
                                <td className="py-2 px-3 whitespace-nowrap text-gray-600">
                                    {new Date(l.created_at_utc).toLocaleString()}
                                </td>
                                <td className="py-2 px-3 font-medium text-blue-600">{l.actor_user_id || "System"}</td>
                                <td className="py-2 px-3">
                                    <span className="px-2 py-0.5 rounded bg-gray-200 text-gray-800 text-xs font-mono uppercase">
                                        {l.action}
                                    </span>
                                </td>
                                <td className="py-2 px-3 text-gray-600">
                                    {l.entity_type} <span className="text-xs text-gray-400">#{l.entity_id}</span>
                                </td>
                                <td className="py-2 px-3 text-xs text-gray-500 font-mono w-1/3 truncate" title={l.details}>
                                    {l.details}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

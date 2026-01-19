import { useEffect, useState } from "react";
import { apiGet } from "../api";

/* --- HELPER COMPONENTS (Reused or adapted from Tickets.jsx) --- */

function SourceIcon({ source }) {
  const isAuto = source === "AUTO";
  return (
    <div className="flex items-center gap-2">
      <div title={isAuto ? "Auto-generated" : "Manually created"}
        className={`p-1.5 rounded-md ${isAuto ? "bg-purple-100 text-purple-600" : "bg-blue-100 text-blue-600"}`}>
        {isAuto ? (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
        ) : (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
        )}
      </div>
      <span className="text-xs font-medium text-gray-600">{isAuto ? "System" : "Manual"}</span>
    </div>
  );
}

function StatusBadge({ s }) {
  return <span className="px-2 py-1 rounded text-xs font-bold tracking-wide bg-gray-100 text-gray-500">{s}</span>;
}

export default function ClosedTickets({ onBack, onOpenTicket, onOpenHistory }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  async function loadList() {
    setLoading(true);
    setErr("");
    try {
      const r = await apiGet("/ui/tickets/list?status=CLOSED&limit=100");
      setItems(r.items || []);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadList(); }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={onBack} className="text-blue-600 hover:text-blue-800 flex items-center gap-1 text-sm font-medium mb-1">
            &larr; Back to Open Tickets
          </button>
          <h2 className="text-2xl font-bold text-gray-800">Closed Tickets Archive</h2>
          <p className="text-sm text-gray-500 mt-1">Showing all previously resolved tickets</p>
        </div>
        <button onClick={loadList} className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 py-2 px-3 rounded-lg">
          Refresh
        </button>
      </div>

      {err && <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">{err}</div>}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
            <tr>
              <th className="px-6 py-3">Source</th>
              <th className="px-6 py-3">Asset</th>
              <th className="px-6 py-3">Details</th>
              <th className="px-6 py-3">Department</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Closed On</th>
              <th className="px-6 py-3">Owner</th>
              <th className="px-6 py-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && <tr><td colSpan={8} className="p-8 text-center text-gray-500">Loading closed tickets...</td></tr>}
            {!loading && items.length === 0 && <tr><td colSpan={8} className="p-8 text-center text-gray-500 italic">No closed tickets found.</td></tr>}

            {items.map(t => (
              <tr key={t.id} className="hover:bg-gray-50 transition-colors group">
                <td className="px-6 py-4"><SourceIcon source={t.source || "MANUAL"} /></td>
                <td className="px-6 py-4">
                  <div className="font-bold text-gray-900">{t.asset_id}</div>
                  <div className="text-xs text-gray-400">{t.site_code}</div>
                </td>
                <td className="px-6 py-4">
                  <div className="font-medium text-gray-800 max-w-xs truncate">{t.title}</div>
                  <div className={`text-xs inline-block mt-1 px-1.5 rounded ${t.priority === 'HIGH' ? 'bg-red-100 text-red-700' : t.priority === 'CRITICAL' ? 'bg-red-800 text-white' : 'bg-gray-100 text-gray-500'}`}>
                    {t.priority}
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">{t.assigned_dept || "-"}</td>
                <td className="px-6 py-4"><StatusBadge s={t.status} /></td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {new Date(t.created_at_utc).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {t.assigned_to || (t.source === "AUTO" ? "System" : "Unassigned")}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <button onClick={() => onOpenTicket(t.id)} className="text-blue-600 hover:text-blue-800 font-bold text-sm">
                      View
                    </button>
                    <span className="text-gray-300 select-none">|</span>
                    <button onClick={() => onOpenHistory(t.asset_id)} className="text-purple-600 hover:text-purple-800 font-bold text-sm">
                      History
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

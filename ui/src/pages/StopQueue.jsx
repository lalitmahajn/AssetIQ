import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";

export default function StopQueue() {
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");
  const [resolution, setResolution] = useState({});
  const [loading, setLoading] = useState(true);

  async function load() {
    setErr("");
    setLoading(true);
    try {
      const r = await apiGet("/ui/stop-queue/list?status=OPEN&limit=50&offset=0");
      setItems(r.items || []);
    } catch (e) {
      setErr(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  }

  async function resolve(id) {
    setErr("");
    try {
      await apiPost("/ui/stop-queue/resolve", { stop_queue_id: id, resolution_text: resolution[id] || "Resolved" });
      await load();
    } catch (e) {
      setErr(String(e?.message || e));
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Stop Queue</h2>
          <p className="text-gray-500 text-sm">Open machine stops requiring attention</p>
        </div>
        <button
          onClick={load}
          className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {err && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {err}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wider">Asset</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wider">Reason</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wider">Opened</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">No open stops</td></tr>
            ) : items.map(x => (
              <tr key={x.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 font-medium text-gray-900">{x.asset_id}</td>
                <td className="px-6 py-4 text-gray-600 max-w-xs truncate">{x.reason}</td>
                <td className="px-6 py-4 text-gray-500 text-sm">{new Date(x.opened_at_utc).toLocaleString()}</td>
                <td className="px-6 py-4">
                  <div className="flex gap-2">
                    <input
                      placeholder="Resolution note"
                      value={resolution[x.id] || ""}
                      onChange={(e) => setResolution({ ...resolution, [x.id]: e.target.value })}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <button
                      onClick={() => resolve(x.id)}
                      className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
                    >
                      Resolve
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

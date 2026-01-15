
import React, { useEffect, useState, useRef } from "react";
import { apiGet, apiPost } from "../api";

/* --- HELPER COMPONENTS --- */

function SlaTimer({ due }) {
  const [rem, setRem] = useState("");
  const [color, setColor] = useState("text-gray-500");

  useEffect(() => {
    if (!due) return;
    const tick = () => {
      const diff = new Date(due) - new Date();
      if (diff <= 0) {
        setRem("BREACHED");
        setColor("text-red-600 font-bold");
        return;
      }
      const hrs = Math.floor(diff / 3600000);
      const mins = Math.floor((diff % 3600000) / 60000);
      setRem(`${hrs}h ${mins}m`);
      if (hrs < 1) setColor("text-orange-600 font-semibold"); // < 1 hour
      else setColor("text-green-600");
    };
    tick();
    const i = setInterval(tick, 60000);
    return () => clearInterval(i);
  }, [due]);

  if (!due) return <span className="text-gray-400 text-xs">No SLA</span>;
  return <span className={`text-xs ${color}`}>{rem}</span>;
}

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
  const map = {
    OPEN: "bg-blue-100 text-blue-700",
    ACK: "bg-yellow-100 text-yellow-700",
    CLOSED: "bg-gray-100 text-gray-500",
  };
  return <span className={`px-2 py-1 rounded text-xs font-bold tracking-wide ${map[s] || "bg-gray-100"}`}>{s}</span>;
}

function AssetHistoryView({ assetId, onBack }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const h = await apiGet(`/ui/assets/${assetId}/history?limit=20`);
        setHistory(h || []);
      } catch (e) { }
      finally { setLoading(false); }
    };
    load();
  }, [assetId]);

  const renderPayload = (payload) => {
    if (!payload) return null;
    return (
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs bg-gray-50 p-2 rounded border border-gray-100">
        {Object.entries(payload).map(([key, val]) => (
          <div key={key} className="flex flex-col">
            <span className="text-gray-400 uppercase font-bold text-[10px]">{key.replace(/_/g, ' ')}</span>
            <span className="text-gray-700 font-medium">{String(val)}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={onBack} className="text-blue-600 hover:text-blue-800 flex items-center gap-1 text-sm font-medium mb-1">
            &larr; Back to Tickets
          </button>
          <h2 className="text-2xl font-bold text-gray-800">Asset History: <span className="text-blue-600">{assetId}</span></h2>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <span className="text-sm font-bold text-gray-500 uppercase">Recent Activity Log</span>
          <span className="text-xs text-gray-400">{history.length} events found</span>
        </div>

        <div className="divide-y divide-gray-100">
          {loading && <div className="p-12 text-center text-gray-500">Loading comprehensive history...</div>}
          {!loading && history.length === 0 && <div className="p-12 text-center text-gray-500 italic">No historical events recorded for this asset.</div>}

          {history.map(h => (
            <div key={h.id} className="p-6 hover:bg-gray-50 transition-colors">
              <div className="flex items-start gap-4">
                <div className={`mt-1 w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-lg
                  ${h.type.includes('STOP') ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'}`}>
                  {h.type.includes('STOP') ? 'S' : 'T'}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-bold text-gray-900 text-lg uppercase tracking-tight">{h.type.replace(/_/g, ' ')}</h4>
                      <p className="text-sm text-gray-500 font-medium">{new Date(h.occurred_at).toLocaleDateString()} &bull; {new Date(h.occurred_at).toLocaleTimeString()}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest
                      ${h.type.includes('STOP') ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}>
                      {h.type.split('_')[0]}
                    </span>
                  </div>

                  <div className="mt-3 text-gray-700 font-medium">
                    {h.payload.title || h.payload.reason || "Automatic System Log"}
                  </div>

                  {renderPayload(h.payload)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* --- MAIN COMPONENT --- */

export default function Tickets() {
  const [view, setView] = useState("LIST"); // LIST | DETAIL | HISTORY
  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [selectedAssetId, setSelectedAssetId] = useState(null);

  // List State
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [myTasksOnly, setMyTasksOnly] = useState(false);
  const [err, setErr] = useState("");

  // Create Form State
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newAsset, setNewAsset] = useState("");
  const [newPriority, setNewPriority] = useState("MEDIUM");

  // Suggestion State
  const [assetSuggestions, setAssetSuggestions] = useState([]);
  const [showAssetDrop, setShowAssetDrop] = useState(false);

  // History State
  const [history, setHistory] = useState([]);

  // No longer using modal
  // const [historyModalAsset, setHistoryModalAsset] = useState(null);

  // Load History Effect
  useEffect(() => {
    if (!newAsset || newAsset.length < 3) { setHistory([]); return; }
    // Only fetch if it looks like a valid ID (not partial search)
    const fetchHist = async () => {
      try {
        const h = await apiGet(`/ui/assets/${newAsset}/history?limit=5`);
        setHistory(h || []);
      } catch (e) { }
    };
    // Debounce slightly to avoid blast
    const t = setTimeout(fetchHist, 500);
    return () => clearTimeout(t);
  }, [newAsset]);

  const currentUser = "admin"; // TODO: Get from context/auth

  async function loadList() {
    setLoading(true);
    setErr("");
    try {
      const r = await apiGet("/ui/tickets/list?limit=50");
      setItems(r.items || []);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadList(); }, []);

  // Filtered Items
  const filteredItems = myTasksOnly
    ? items.filter(i => i.assigned_to === currentUser)
    : items;

  // Handlers
  async function doCreate(e) {
    e.preventDefault();
    try {
      await apiPost("/ui/tickets/create", { title: newTitle, asset_id: newAsset, priority: newPriority });
      setShowCreate(false);
      setNewTitle(""); setNewAsset("");
      loadList();
    } catch (e) { setErr(e.message); }
  }

  async function searchAssets(q) {
    setNewAsset(q);
    if (q.length < 2) { setAssetSuggestions([]); setShowAssetDrop(false); return; }
    try {
      const r = await apiGet(`/master/assets/list?q=${q}&limit=5`);
      setAssetSuggestions(r || []);
      setShowAssetDrop(true);
    } catch (e) { }
  }

  if (view === "DETAIL" && selectedTicketId) {
    return <TicketDetail
      id={selectedTicketId}
      onBack={() => { setView("LIST"); setSelectedTicketId(null); loadList(); }}
      currentUser={currentUser}
    />;
  }

  if (view === "HISTORY" && selectedAssetId) {
    return <AssetHistoryView
      assetId={selectedAssetId}
      onBack={() => { setView("LIST"); setSelectedAssetId(null); loadList(); }}
    />;
  }

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Tickets</h2>
          <div className="flex items-center gap-4 mt-1">
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
              <input type="checkbox" checked={myTasksOnly} onChange={e => setMyTasksOnly(e.target.checked)} className="rounded text-blue-600 focus:ring-blue-500" />
              Show only my tasks
            </label>
            <span className="text-gray-300">|</span>
            <span className="text-sm text-gray-500">{filteredItems.length} open tickets</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowCreate(!showCreate)} className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg shadow-sm transition-colors">
            + New Ticket
          </button>
          <button onClick={loadList} className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 py-2 px-3 rounded-lg">
            Refresh
          </button>
        </div>
      </div>

      {err && <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">{err}</div>}

      {/* CREATE FORM */}
      {showCreate && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in-down mb-6">
          {/* Form Column */}
          <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <form onSubmit={doCreate}>
              <h3 className="font-bold text-gray-800 mb-4">Create Manual Ticket</h3>
              <div className="grid grid-cols-1 gap-4">
                <div className="relative">
                  <label className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1 block">Asset ID</label>
                  <input
                    className="w-full h-10 border border-gray-300 rounded-lg px-4 focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g. AST-001"
                    value={newAsset}
                    onChange={e => searchAssets(e.target.value)}
                    required
                    autoComplete="off"
                  />
                  {showAssetDrop && assetSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 w-full bg-white border shadow-lg rounded-md mt-1 z-10">
                      {assetSuggestions.map(a => (
                        <div key={a.id} onClick={() => { setNewAsset(a.id); setShowAssetDrop(false); }} className="p-2 hover:bg-gray-50 cursor-pointer text-sm font-medium">
                          {a.id} <span className="text-gray-400 font-normal">- {a.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1 block">Issue Title</label>
                  <input
                    className="w-full h-10 border border-gray-300 rounded-lg px-4 focus:ring-2 focus:ring-blue-500"
                    placeholder="Describe the issue..."
                    value={newTitle}
                    onChange={e => setNewTitle(e.target.value)}
                    required
                  />
                </div>
                <div className="flex gap-2 items-end">
                  <div className="flex-1">
                    <label className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1 block">Priority</label>
                    <select value={newPriority} onChange={e => setNewPriority(e.target.value)} className="w-full h-10 border border-gray-300 rounded-lg px-4 bg-white">
                      <option value="LOW">Low</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="HIGH">High</option>
                      <option value="CRITICAL">Critical</option>
                    </select>
                  </div>
                  <button type="submit" className="h-10 bg-green-600 text-white px-6 rounded-lg font-medium hover:bg-green-700 transition-colors shadow-sm">
                    Create
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* History Column */}
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
            <h4 className="font-bold text-gray-700 text-sm mb-3">Asset History</h4>
            {history.length === 0 ? (
              <p className="text-xs text-gray-400 italic">No recent history or invalid asset.</p>
            ) : (
              <ul className="space-y-3">
                {history.map(h => (
                  <li key={h.id} className="text-xs border-b border-gray-200 pb-2 last:border-0">
                    <div className="flex justify-between text-gray-400 mb-0.5">
                      <span>{new Date(h.occurred_at).toLocaleDateString()}</span>
                      <span className={`font-bold ${h.type.includes('STOP') ? 'text-red-500' : 'text-blue-500'}`}>{h.type}</span>
                    </div>
                    <div className="text-gray-700 truncate" title={h.payload.reason || h.payload.title || "No details"}>
                      {h.payload.reason || h.payload.title || "Event"}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* LIST */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
            <tr>
              <th className="px-6 py-3">Source</th>
              <th className="px-6 py-3">Asset</th>
              <th className="px-6 py-3">Details</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">SLA Due</th>
              <th className="px-6 py-3">Owner</th>
              <th className="px-6 py-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && <tr><td colSpan={7} className="p-8 text-center text-gray-500">Loading tickets...</td></tr>}
            {!loading && filteredItems.length === 0 && <tr><td colSpan={7} className="p-8 text-center text-gray-500">No tickets found.</td></tr>}

            {filteredItems.map(t => (
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
                <td className="px-6 py-4"><StatusBadge s={t.status} /></td>
                <td className="px-6 py-4 font-mono"><SlaTimer due={t.sla_due_at_utc} /></td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {t.assigned_to ? (
                    t.assigned_to
                  ) : (
                    t.source === "AUTO" ? (
                      <span className="text-purple-600 font-medium">System</span>
                    ) : (
                      <span className="italic opacity-50">Unassigned</span>
                    )
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <button onClick={() => { setSelectedTicketId(t.id); setView("DETAIL"); }} className="text-blue-600 hover:text-blue-800 font-bold text-sm">
                      Open
                    </button>
                    <span className="text-gray-300 select-none">|</span>
                    <button onClick={() => { setSelectedAssetId(t.asset_id); setView("HISTORY"); }} className="text-purple-600 hover:text-purple-800 font-bold text-sm">
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

/* --- DETAIL COMPONENT --- */

function TicketDetail({ id, onBack, currentUser }) {
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");

  async function reload() {
    setLoading(true);
    try {
      const data = await apiGet(`/ui/tickets/${id}/details`);
      setD(data);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { reload(); }, [id]);

  async function doAck() {
    try {
      await apiPost("/ui/tickets/acknowledge", { ticket_id: id });
      reload();
    } catch (e) { alert(e.message); }
  }

  async function doClose() {
    if (!reason) return alert("Please select a resolution reason.");
    try {
      await apiPost("/ui/tickets/close", { ticket_id: id, close_note: note || "Resolved", resolution_reason: reason });
      onBack(); // Go back to list on close
    } catch (e) { alert(e.message); }
  }

  if (loading) return <div className="p-8 text-center">Loading details...</div>;
  if (!d) return <div className="p-8 text-red-600">Failed to load ticket.</div>;

  const t = d.ticket;
  const acts = d.activity || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in-up">
      {/* LEFT: INFO & ACTIONS */}
      <div className="lg:col-span-2 space-y-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <div className="flex justify-between items-start mb-4">
            <button onClick={onBack} className="text-gray-500 hover:text-gray-800 flex items-center gap-1 text-sm font-medium mb-2">
              &larr; Back to List
            </button>
            <StatusBadge s={t.status} />
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">{t.title}</h1>
          <div className="flex gap-4 text-sm text-gray-600 mb-6 font-mono">
            <span>ID: {t.id}</span>
            <span>&bull;</span>
            <span>Asset: <span className="font-bold text-gray-900">{t.asset_id}</span></span>
            <span>&bull;</span>
            <span>SLA: <SlaTimer due={t.sla_due_at_utc} /></span>
          </div>

          {t.status === "OPEN" && (
            <div className="bg-blue-50 border border-blue-100 p-4 rounded-lg flex items-center justify-between">
              <div>
                <p className="text-blue-900 font-semibold">New Ticket</p>
                <p className="text-blue-700 text-sm">Acknowledge this ticket to start working on it.</p>
              </div>
              <button onClick={doAck} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium shadow-sm">
                Acknowledge
              </button>
            </div>
          )}

          {t.status === "ACK" && (
            <div className="bg-green-50 border border-green-100 p-6 rounded-lg space-y-4">
              <h3 className="font-bold text-green-900">Resolve Ticket</h3>

              <div>
                <label className="block text-xs font-semibold uppercase text-green-800 mb-1">Root Cause (Reason)</label>
                <select
                  className="w-full border-gray-300 rounded-lg p-2"
                  value={reason}
                  onChange={e => setReason(e.target.value)}
                >
                  <option value="">-- Select Reason --</option>
                  <option value="Machine Wear">Machine Wear</option>
                  <option value="Operator Error">Operator Error</option>
                  <option value="Material Defect">Material Defect</option>
                  <option value="Software Glitch">Software Glitch</option>
                  <option value="Unpreventable">Unpreventable (External)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-green-800 mb-1">Resolution Notes</label>
                <textarea
                  className="w-full border-gray-300 rounded-lg p-2 h-20"
                  placeholder="What action did you take?"
                  value={note}
                  onChange={e => setNote(e.target.value)}
                />
              </div>

              <button onClick={doClose} className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg font-bold shadow-sm">
                Close Ticket
              </button>
            </div>
          )}

          {t.status === "CLOSED" && (
            <div className="bg-gray-100 p-4 rounded-lg text-gray-600 text-sm">
              <span className="font-bold">Closed:</span> {t.resolution_reason || "No Reason"} - {t.close_note}
            </div>
          )}
        </div>
      </div>

      {/* RIGHT: TIMELINE */}
      <div className="bg-white rounded-xl border border-gray-200 flex flex-col h-[600px] shadow-sm">
        <div className="p-4 border-b border-gray-100 font-bold text-gray-800">Activity History</div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {acts.map(a => (
            <div key={a.id} className="flex gap-3">
              <div className="flex-shrink-0 mt-1">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white
                                    ${a.type === 'CREATED' ? 'bg-purple-500' : a.type === 'ACK' ? 'bg-blue-500' : a.type === 'CLOSED' ? 'bg-green-500' : 'bg-gray-400'}`}>
                  {a.type[0]}
                </div>
              </div>
              <div className="flex-1 bg-white p-3 rounded-lg border border-gray-200 shadow-sm text-sm">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-gray-900">{a.type}</span>
                  <span className="text-xs text-gray-400">{new Date(a.created_at_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <p className="text-gray-600">{a.details}</p>
                {a.actor && <div className="mt-2 text-xs text-gray-400 font-mono">By: {a.actor}</div>}
              </div>
            </div>
          ))}
          <div className="text-center text-xs text-gray-400 pt-4">End of history</div>
        </div>
      </div>
    </div>
  );
}

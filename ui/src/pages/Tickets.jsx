
import { useEffect, useState, Suspense, lazy } from "react";
import { apiGet, apiPost } from "../api";

// Lazy load to optimize bundle size
const AssetHistoryView = lazy(() => import("../components/AssetHistoryView"));
const ClosedTickets = lazy(() => import("./ClosedTickets"));

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

      if (hrs < 1) {
        setRem(`[WARNING] ${hrs}h ${mins}m`);
        setColor("text-orange-600 font-bold");
      } else {
        setRem(`[OK] ${hrs}h ${mins}m`);
        setColor("text-green-600 font-medium");
      }
    };
    tick();
    const i = setInterval(tick, 60000);
    return () => clearInterval(i);
  }, [due]);

  if (!due) return <span className="text-gray-400 text-sm">No SLA</span>;
  return <span className={`text-sm ${color} font-bold`}>{rem}</span>;
}

function timeAgo(dateStr) {
  if (!dateStr) return "-";
  const diff = new Date() - new Date(dateStr);
  const mins = Math.floor(diff / 60000);
  const hrs = Math.floor(mins / 60);
  const days = Math.floor(hrs / 24);

  if (days > 0) return `${days}d ago`;
  if (hrs > 0) return `${hrs}h ago`;
  if (mins > 0) return `${mins}m ago`;
  return "Just now";
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


/* --- MAIN COMPONENT --- */

export default function Tickets({ plantName }) {
  const [view, setView] = useState("LIST"); // LIST | DETAIL | HISTORY | CLOSED_LIST
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
  const [newDept, setNewDept] = useState("");

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    source: "",
    asset_id: "",
    dept: "",
    status: "",
    sla: "", // BREACHED, WARNING, OK
    owner: "" // Text search
  });

  // Suggestion State
  const [assetSuggestions, setAssetSuggestions] = useState([]);
  const [showAssetDrop, setShowAssetDrop] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  // Dynamic Masters State
  const [departments, setDepartments] = useState([]);
  const [resolutionReasons, setResolutionReasons] = useState([]);

  // "Other" custom text state
  const [customDept, setCustomDept] = useState("");

  // History State
  const [history, setHistory] = useState([]);

  // Fetch Dynamic Masters on mount
  useEffect(() => {
    apiGet("/masters-dynamic/items?type_code=DEPARTMENT")
      .then(data => setDepartments(data || []))
      .catch(() => setDepartments([]));
    apiGet("/masters-dynamic/items?type_code=RESOLUTION_REASON")
      .then(data => setResolutionReasons(data || []))
      .catch(() => setResolutionReasons([]));
  }, []);

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
  const filteredItems = items.filter(t => {
    // 1. My Tasks
    if (myTasksOnly && t.assigned_to !== currentUser) return false;

    // 2. Filters
    if (filters.source && t.source !== filters.source) return false;
    if (filters.asset_id && !t.asset_id.toLowerCase().includes(filters.asset_id.toLowerCase())) return false;
    if (filters.dept && t.assigned_dept !== filters.dept) return false;
    if (filters.status && t.status !== filters.status) return false;
    if (filters.owner && !(t.assigned_to || "").toLowerCase().includes(filters.owner.toLowerCase())) return false;

    if (filters.sla) {
      // Compute SLA state locally to match Timer logic roughly
      const due = t.sla_due_at_utc ? new Date(t.sla_due_at_utc) : null;
      if (!due) return false; // Can't filter by SLA if no SLA
      const now = new Date();
      const diff = due - now;

      let state = "OK";
      if (diff <= 0) state = "BREACHED";
      else if (diff < 3600000) state = "WARNING"; // < 1hr

      if (filters.sla !== state) return false;
    }

    return true;
  });

  // Handlers
  async function doCreate(e) {
    e.preventDefault();
    // Use customDept if "Other" was selected
    const finalDept = newDept === "__OTHER__" ? customDept : newDept;
    try {
      await apiPost("/ui/tickets/create", { title: newTitle, asset_id: newAsset, priority: newPriority, dept: finalDept });
      setShowCreate(false);
      setNewTitle(""); setNewAsset(""); setNewDept(""); setCustomDept("");
      loadList();
    } catch (e) { setErr(e.message); }
  }

  async function searchAssets(q) {
    setNewAsset(q);
    if (q.length < 2) {
      setAssetSuggestions([]);
      setShowAssetDrop(false);
      return;
    }
    setIsSearching(true);
    try {
      const r = await apiGet(`/master/assets/list?q=${q}&limit=5`);
      setAssetSuggestions(r || []);
      setShowAssetDrop(true);
    } catch (e) {
    } finally {
      setIsSearching(false);
    }
  }

  if (view === "DETAIL" && selectedTicketId) {
    // TicketDetail remains bundled as it is local function
    return <TicketDetail
      id={selectedTicketId}
      onBack={() => { setView("LIST"); setSelectedTicketId(null); loadList(); }}
      currentUser={currentUser}
    />;
  }

  if (view === "HISTORY" && selectedAssetId) {
    return (
      <Suspense fallback={<div className="p-12 text-center text-gray-400">Loading History...</div>}>
        <AssetHistoryView
          assetId={selectedAssetId}
          onBack={() => { setView("LIST"); setSelectedAssetId(null); loadList(); }}
        />
      </Suspense>
    );
  }

  if (view === "CLOSED_LIST") {
    return (
      <Suspense fallback={<div className="p-12 text-center text-gray-400">Loading Closed Tickets...</div>}>
        <ClosedTickets
          onBack={() => { setView("LIST"); loadList(); }}
          onOpenTicket={(id) => { setSelectedTicketId(id); setView("DETAIL"); }}
          onOpenHistory={(assetId) => { setSelectedAssetId(assetId); setView("HISTORY"); }}
        />
      </Suspense>
    );
  }

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Tickets</h2>
          <div className="flex items-center gap-4 mt-1">
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
              <input type="checkbox" checked={myTasksOnly} onChange={e => setMyTasksOnly(e.target.checked)} className="rounded text-blue-600 focus:ring-blue-500" />
              Show only my tasks
            </label>
            <span className="text-gray-300">|</span>
            <span className="text-sm text-gray-500">{filteredItems.length} open tickets</span>
            <span className="text-sm text-gray-500">{filteredItems.length} open tickets</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowFilters(!showFilters)} className={`border hover:bg-gray-50 text-gray-700 py-2 px-3 rounded-lg flex items-center gap-2 transition-colors ${showFilters ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-white border-gray-300'}`}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
            Filters
          </button>
          <button onClick={() => setView("CLOSED_LIST")} className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 py-2 px-4 rounded-lg shadow-sm transition-colors flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" /></svg>
            Closed Tickets
          </button>
          <button onClick={() => setShowCreate(!showCreate)} className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg shadow-sm transition-colors">
            + New Ticket
          </button>
          <button onClick={loadList} className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 py-2 px-3 rounded-lg">
            Refresh
          </button>
        </div>
      </div>

      {/* FILTER BAR */}
      {showFilters && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm animate-fade-in-down grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div>
            <label className="text-xs font-bold text-gray-500 uppercase block mb-1">Source</label>
            <select className="w-full text-sm border-gray-300 rounded-md" value={filters.source} onChange={e => setFilters({ ...filters, source: e.target.value })}>
              <option value="">All Sources</option>
              <option value="MANUAL">Manual</option>
              <option value="AUTO">System</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-bold text-gray-500 uppercase block mb-1">Asset ID</label>
            <input className="w-full text-sm border-gray-300 rounded-md" placeholder="Search..." value={filters.asset_id} onChange={e => setFilters({ ...filters, asset_id: e.target.value })} />
          </div>
          <div>
            <label className="text-xs font-bold text-gray-500 uppercase block mb-1">Department</label>
            <select className="w-full text-sm border-gray-300 rounded-md" value={filters.dept} onChange={e => setFilters({ ...filters, dept: e.target.value })}>
              <option value="">All Depts</option>
              {departments.map(d => (
                <option key={d.id} value={d.item_name}>{d.item_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-bold text-gray-500 uppercase block mb-1">Status</label>
            <select className="w-full text-sm border-gray-300 rounded-md" value={filters.status} onChange={e => setFilters({ ...filters, status: e.target.value })}>
              <option value="">All Active</option>
              <option value="OPEN">Open</option>
              <option value="ACK">Acknowledged</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-bold text-gray-500 uppercase block mb-1">SLA State</label>
            <select className="w-full text-sm border-gray-300 rounded-md" value={filters.sla} onChange={e => setFilters({ ...filters, sla: e.target.value })}>
              <option value="">All States</option>
              <option value="BREACHED">Breached</option>
              <option value="WARNING">Warning</option>
              <option value="OK">On Track</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-bold text-gray-500 uppercase block mb-1">Owner</label>
            <input className="w-full text-sm border-gray-300 rounded-md" placeholder="Search owner..." value={filters.owner} onChange={e => setFilters({ ...filters, owner: e.target.value })} />
          </div>
          {/* Clear Filters */}
          <div className="col-span-full flex justify-end">
            <button onClick={() => setFilters({ source: "", asset_id: "", dept: "", status: "", sla: "", owner: "" })} className="text-xs text-red-600 hover:underline font-medium">Clear Filters</button>
          </div>
        </div>
      )}

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
                  {/* New Asset Indicator */}
                  {!isSearching && newAsset.length >= 3 && !assetSuggestions.some(a => (a.asset_code || a.id).toLowerCase() === newAsset.toLowerCase()) && (
                    <div className="absolute top-1 right-0 text-xs font-medium text-blue-600 animate-pulse">
                      New Asset being created
                    </div>
                  )}
                  {showAssetDrop && assetSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 w-full bg-white border shadow-lg rounded-md mt-1 z-10">
                      {assetSuggestions.map(a => (
                        <div key={a.id} onClick={() => { setNewAsset(a.asset_code || a.id); setShowAssetDrop(false); }} className="p-2 hover:bg-gray-50 cursor-pointer text-sm font-medium">
                          {a.asset_code || a.id} <span className="text-gray-400 font-normal">- {a.name}</span>
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
                  <div className="flex-1">
                    <label className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1 block">Department</label>
                    <select value={newDept} onChange={e => {
                      setNewDept(e.target.value);
                      if (e.target.value !== "__OTHER__") setCustomDept("");
                    }} className="w-full h-10 border border-gray-300 rounded-lg px-4 bg-white">
                      <option value="">-- Select --</option>
                      {departments.map(d => (
                        <option key={d.id} value={d.item_name}>{d.item_name}</option>
                      ))}
                      <option value="__OTHER__">Other (specify)</option>
                    </select>
                    {newDept === "__OTHER__" && (
                      <input
                        className="w-full h-10 border border-gray-300 rounded-lg px-4 mt-2 bg-white"
                        placeholder="Enter department name..."
                        value={customDept}
                        onChange={e => setCustomDept(e.target.value)}
                      />
                    )}
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
          <thead className="bg-gray-50 border-b border-gray-100 text-left text-xs font-bold text-gray-400 uppercase tracking-widest">
            <tr>
              <th className="px-6 py-4">Source</th>
              <th className="px-6 py-4">Asset</th>
              <th className="px-6 py-4">Details</th>
              <th className="px-6 py-4">Created</th>
              <th className="px-6 py-4">Department</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">SLA Due</th>
              <th className="px-6 py-4">Owner</th>
              <th className="px-6 py-4">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && <tr><td colSpan={8} className="p-8 text-center text-gray-500">Loading tickets...</td></tr>}
            {!loading && filteredItems.length === 0 && <tr><td colSpan={8} className="p-8 text-center text-gray-500">No tickets found.</td></tr>}

            {filteredItems.map(t => (
              <tr key={t.id} className="hover:bg-gray-50 transition-colors group">
                <td className="px-6 py-4"><SourceIcon source={t.source || "MANUAL"} /></td>
                <td className="px-6 py-4">
                  <div className="text-xs font-mono text-blue-600 mb-0.5">{t.ticket_code || t.id}</div>
                  <div className="font-bold text-gray-900">{t.asset_id}</div>
                  <div className="text-xs text-gray-400">{t.site_code}</div>
                </td>
                <td className="px-6 py-4">
                  <div className="font-medium text-gray-800 max-w-xs truncate">{t.title}</div>
                  <div className={`text-xs inline-block mt-1 px-1.5 rounded ${t.priority === 'HIGH' ? 'bg-red-100 text-red-700' : t.priority === 'CRITICAL' ? 'bg-red-800 text-white' : 'bg-gray-100 text-gray-500'}`}>
                    {t.priority}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-gray-900 font-medium text-sm">
                    {new Date(t.created_at_utc).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </div>
                  <div className="text-xs text-blue-600 font-semibold mt-0.5">
                    {timeAgo(t.created_at_utc)}
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">{t.assigned_dept || "-"}</td>
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
  const [resolutionReasons, setResolutionReasons] = useState([]);
  const [customReason, setCustomReason] = useState("");

  async function reload() {
    setLoading(true);
    try {
      const data = await apiGet(`/ui/tickets/${id}/details`);
      setD(data);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { reload(); }, [id]);

  // Fetch resolution reasons for close dropdown
  useEffect(() => {
    apiGet("/masters-dynamic/items?type_code=RESOLUTION_REASON")
      .then(data => setResolutionReasons(data || []))
      .catch(() => setResolutionReasons([]));
  }, []);

  async function doAck() {
    try {
      await apiPost("/ui/tickets/acknowledge", { ticket_id: id });
      reload();
    } catch (e) { alert(e.message); }
  }

  async function doClose() {
    if (!reason) return alert("Please select a resolution reason.");
    if (!note || !note.trim()) return alert("Please enter resolution notes.");
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
    <>
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
              <span>ID: <span className="font-bold text-gray-800">{t.ticket_code || t.id}</span></span>
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
                  <label className="block text-xs font-semibold uppercase text-green-800 mb-1">Root Cause (Reason) <span className="text-red-500">*</span></label>
                  <select
                    className="w-full border-gray-300 rounded-lg p-2"
                    value={reason}
                    onChange={e => {
                      setReason(e.target.value);
                      if (e.target.value !== "__OTHER__") setCustomReason("");
                    }}
                  >
                    <option value="">-- Select Reason --</option>
                    {resolutionReasons.map(r => (
                      <option key={r.id} value={r.item_name}>{r.item_name}</option>
                    ))}
                    <option value="__OTHER__">Other (specify)</option>
                  </select>
                  {reason === "__OTHER__" && (
                    <input
                      className="w-full border-gray-300 rounded-lg p-2 mt-2"
                      placeholder="Enter resolution reason..."
                      value={customReason}
                      onChange={e => setCustomReason(e.target.value)}
                    />
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-green-800 mb-1">Resolution Notes <span className="text-red-500">*</span></label>
                  <textarea
                    className="w-full border-gray-300 rounded-lg p-2 h-20"
                    placeholder="What action did you take?"
                    value={note}
                    onChange={e => setNote(e.target.value)}
                  />
                </div>

                <button
                  onClick={() => {
                    // Use customReason if "Other" was selected
                    const finalReason = reason === "__OTHER__" ? customReason : reason;
                    apiPost("/ui/tickets/close", { ticket_id: id, close_note: note, resolution_reason: finalReason })
                      .then(reload)
                      .catch(e => setErr(e.message));
                  }}
                  className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg font-bold shadow-sm"
                >
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
    </>
  );
}

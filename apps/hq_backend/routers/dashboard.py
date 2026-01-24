import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import desc, func, select

from apps.hq_backend.models import PlantRegistry, RollupDaily, StopReasonDaily, TicketSnapshot
from common_core.db import HQSessionLocal
from common_core.security import verify_jwt

router = APIRouter(prefix="/hq", tags=["hq-dashboard"])


def _get_current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get("hq_access_token")
    if not token:
        # Check Authorization header as fallback for API clients
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="NOT_AUTHENTICATED")

    try:
        payload = verify_jwt(token)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN") from None


def _today_utc() -> str:
    return datetime.utcnow().date().isoformat()


@router.get("/plants")
def plants(user: dict[str, Any] = Depends(_get_current_user)) -> dict[str, Any]:
    db = HQSessionLocal()
    try:
        rows = db.execute(select(PlantRegistry).order_by(PlantRegistry.site_code)).scalars().all()
        items = []
        for p in rows:
            items.append(
                {
                    "site_code": p.site_code,
                    "display_name": p.display_name,
                    "is_active": bool(p.is_active),
                    "last_seen_at_utc": p.last_seen_at_utc.isoformat()
                    if p.last_seen_at_utc
                    else None,
                }
            )
        return {"items": items}
    finally:
        db.close()


@router.get("/summary")
def summary(
    day_utc: str | None = None, user: dict[str, Any] = Depends(_get_current_user)
) -> dict[str, Any]:
    day = (day_utc or _today_utc())[:10]
    db = HQSessionLocal()
    try:
        # rollups
        rollups = db.execute(select(RollupDaily).where(RollupDaily.day_utc == day)).scalars().all()
        by_site = {r.site_code: r for r in rollups}

        # critical open tickets (OPEN/ACK and priority HIGH/CRITICAL)
        crit = db.execute(
            select(TicketSnapshot.site_code, func.count(TicketSnapshot.id))
            .where(
                TicketSnapshot.status.in_(["OPEN", "ACKNOWLEDGED", "ACK"]),
                TicketSnapshot.priority.in_(["HIGH", "CRITICAL"]),
            )
            .group_by(TicketSnapshot.site_code)
        ).all()
        crit_map = {c[0]: int(c[1] or 0) for c in crit}

        plants = db.execute(select(PlantRegistry).order_by(PlantRegistry.site_code)).scalars().all()
        items: list[dict[str, Any]] = []
        now = datetime.utcnow()
        for p in plants:
            r = by_site.get(p.site_code)
            # status heuristic: stale if last seen > 15 min
            status = "UNKNOWN"
            if p.last_seen_at_utc:
                delta = now - p.last_seen_at_utc
                status = "ONLINE" if delta <= timedelta(minutes=15) else "OFFLINE"
            items.append(
                {
                    "site_code": p.site_code,
                    "display_name": p.display_name,
                    "status": status,
                    "stops": int(r.stops) if r else 0,
                    "downtime_minutes": int(r.downtime_minutes) if r else 0,
                    "sla_breaches": int(r.sla_breaches) if r else 0,
                    "tickets_open": int(r.tickets_open) if r else 0,
                    "critical_open_tickets": int(crit_map.get(p.site_code, 0)),
                    "updated_at_utc": r.updated_at_utc.isoformat()
                    if (r and r.updated_at_utc)
                    else None,
                    "last_seen_at_utc": p.last_seen_at_utc.isoformat()
                    if p.last_seen_at_utc
                    else None,
                }
            )
        return {"day_utc": day, "items": items}
    finally:
        db.close()


@router.get("/compare/downtime")
def compare_downtime(
    day_utc: str | None = None, user: dict[str, Any] = Depends(_get_current_user)
) -> dict[str, Any]:
    day = (day_utc or _today_utc())[:10]
    db = HQSessionLocal()
    try:
        # Join with PlantRegistry to get display_name
        rows = db.execute(
            select(RollupDaily.site_code, RollupDaily.downtime_minutes, PlantRegistry.display_name)
            .join(PlantRegistry, RollupDaily.site_code == PlantRegistry.site_code)
            .where(RollupDaily.day_utc == day)
            .order_by(desc(RollupDaily.downtime_minutes))
        ).all()
        items = [
            {"site_code": r[0], "downtime_minutes": int(r[1] or 0), "display_name": r[2] or r[0]}
            for r in rows
        ]
        return {"day_utc": day, "items": items}
    finally:
        db.close()


@router.get("/rank/sla")
def rank_sla(
    day_utc: str | None = None, user: dict[str, Any] = Depends(_get_current_user)
) -> dict[str, Any]:
    day = (day_utc or _today_utc())[:10]
    db = HQSessionLocal()
    try:
        # Join with PlantRegistry to get display_name
        rows = db.execute(
            select(RollupDaily.site_code, RollupDaily.sla_breaches, PlantRegistry.display_name)
            .join(PlantRegistry, RollupDaily.site_code == PlantRegistry.site_code)
            .where(RollupDaily.day_utc == day)
            .order_by(desc(RollupDaily.sla_breaches))
        ).all()
        items = [
            {"site_code": r[0], "sla_breaches": int(r[1] or 0), "display_name": r[2] or r[0]}
            for r in rows
        ]
        return {"day_utc": day, "items": items}
    finally:
        db.close()


@router.get("/top-reasons")
def top_reasons(
    day_utc: str | None = None, limit: int = 5, user: dict[str, Any] = Depends(_get_current_user)
) -> dict[str, Any]:
    day = (day_utc or _today_utc())[:10]
    limit = max(1, min(int(limit), 20))
    db = HQSessionLocal()
    try:
        rows = db.execute(
            select(
                StopReasonDaily.site_code,
                StopReasonDaily.reason_code,
                StopReasonDaily.stops,
                StopReasonDaily.downtime_minutes,
                PlantRegistry.display_name,
            )
            .join(PlantRegistry, StopReasonDaily.site_code == PlantRegistry.site_code)
            .where(StopReasonDaily.day_utc == day)
            .order_by(desc(StopReasonDaily.downtime_minutes))
        ).all()
        # group
        grouped: dict[str, list[dict[str, Any]]] = {}
        for site_code, reason_code, stops, dtm, display_name in rows:
            label = display_name or site_code
            grouped.setdefault(label, [])
            if len(grouped[label]) < limit:
                grouped[label].append(
                    {
                        "reason_code": reason_code,
                        "stops": int(stops or 0),
                        "downtime_minutes": int(dtm or 0),
                    }
                )
        return {"day_utc": day, "limit": limit, "items": grouped}
    finally:
        db.close()


@router.get("/insights")
def insights(
    day_utc: str | None = None, user: dict[str, Any] = Depends(_get_current_user)
) -> dict[str, Any]:
    day = (day_utc or _today_utc())[:10]
    db = HQSessionLocal()
    try:
        from apps.hq_backend.models import InsightDaily

        rows = db.execute(
            select(InsightDaily, PlantRegistry.display_name)
            .outerjoin(PlantRegistry, InsightDaily.site_code == PlantRegistry.site_code)
            .where(InsightDaily.day_utc == day)
            .order_by(desc(InsightDaily.severity), InsightDaily.id)
        ).all()

        items = []
        for r, display_name in rows:
            items.append(
                {
                    "site_code": r.site_code or "GLOBAL",
                    "display_name": display_name or r.site_code or "GLOBAL",
                    "type": r.insight_type,
                    "title": r.title,
                    "severity": r.severity,
                    "detail": r.detail_json,
                }
            )
        return {"day_utc": day, "items": items}
    finally:
        db.close()


@router.get("/admin", response_class=HTMLResponse)
def admin(user: dict[str, Any] = Depends(_get_current_user)) -> Response:
    roles = user.get("roles", [])
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
    return HTMLResponse(_ADMIN_HTML, headers={"Cache-Control": "no-store, max-age=0"})


@router.get("/ui", response_class=HTMLResponse)
def ui(request: Request) -> Response:
    # Check for token in cookie
    token = request.cookies.get("hq_access_token")
    is_authenticated = False
    roles = []
    if token:
        try:
            payload = verify_jwt(token)
            is_authenticated = True
            roles = payload.get("roles", [])
        except Exception:
            pass

    if not is_authenticated:
        return HTMLResponse(_LOGIN_HTML, headers={"Cache-Control": "no-store, max-age=0"})

    # minimal, no-build UI for management (read-only)
    html = _DASHBOARD_HTML.replace("/*ROLES_INJECT*/", f"const USER_ROLES = {json.dumps(roles)};")
    return HTMLResponse(html, headers={"Cache-Control": "no-store, max-age=0"})


_LOGIN_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>HQ Login - AssetIQ</title>
  <style>
    body{font-family:Arial,Helvetica,sans-serif;margin:0;background:#0b0f14;color:#e6edf3;display:flex;align-items:center;justify-content:center;height:100vh}
    .card{background:#111827;border:1px solid #1f2937;border-radius:10px;padding:24px;width:320px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.1),0 2px 4px -1px rgba(0,0,0,0.06)}
    h1{font-size:20px;margin:0 0 20px 0;text-align:center}
    .field{margin-bottom:16px}
    label{display:block;font-size:12px;color:#9ca3af;margin-bottom:4px}
    input{width:100%;background:#0b1220;border:1px solid #1f2937;color:#e6edf3;border-radius:8px;padding:8px;box-sizing:border-box}
    button{width:100%;background:#2563eb;border:none;color:white;border-radius:8px;padding:10px;cursor:pointer;font-weight:bold;margin-top:12px}
    button:hover{background:#1d4ed8}
    .error{color:#f87171;font-size:12px;margin-top:12px;text-align:center;display:none}
  </style>
</head>
<body>
  <div class="card">
    <h1>AssetIQ HQ Login</h1>
    <div class="field">
      <label>Username</label>
      <input id="username" type="text" placeholder="e.g. admin"/>
    </div>
    <div class="field">
      <label>PIN</label>
      <input id="pin" type="password" placeholder="4+ digits"/>
    </div>
    <button onclick="doLogin()">Login</button>
    <div id="error" class="error"></div>
  </div>
  <script>
    async function doLogin(){
      const username = document.getElementById("username").value.trim();
      const pin = document.getElementById("pin").value.trim();
      const err = document.getElementById("error");
      err.style.display = "none";

      try {
        const r = await fetch("/hq/auth/login", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({username, pin})
        });
        if (!r.ok) {
          const detail = await r.json();
          throw new Error(detail.detail || "Login failed");
        }
        window.location.reload();
      } catch (e) {
        err.textContent = e.message;
        err.style.display = "block";
      }
    }
  </script>
</body>
</html>"""


_DASHBOARD_HTML = r"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>AssetIQ HQ Dashboard</title>
  <style>
    :root { color-scheme: dark; --bg: #0b0f14; --card: #111827; --border: #1f2937; --text: #e6edf3; --muted: #9ca3af; --blue: #2563eb; --blue-dim: #1d4ed8; }
    body{font-family:'Inter',system-ui,-apple-system,sans-serif;margin:20px;background:var(--bg);color:var(--text)}

    .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
    h1{font-size:22px;margin:0;font-weight:700;letter-spacing:-0.5px}

    .controls-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;background:var(--card);padding:10px 16px;border-radius:10px;border:1px solid var(--border)}
    .controls-group{display:flex;gap:12px;align-items:center}

    select, input[type="date"]{background:#0b1220;border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 10px;font-family:inherit}
    button{background:var(--card);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 12px;cursor:pointer;font-weight:500;transition:all 0.2s}
    button:hover{background:var(--border)}
    button.primary{background:var(--blue);border-color:var(--blue);color:white}
    button.primary:hover{background:var(--blue-dim)}
    button.danger{background:#450a0a;border-color:#7f1d1d;color:#fca5a5}
    button.danger:hover{background:#7f1d1d}

    .grid{display:grid;grid-template-columns:repeat(auto-fit, minmax(450px, 1fr));gap:20px}
    .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;display:flex;flex-direction:column}
    .card h2{font-size:14px;text-transform:uppercase;color:var(--muted);margin:0 0 16px 0;letter-spacing:1px;font-weight:600}

    /* Table */
    table{width:100%;border-collapse:collapse;font-size:13px}
    th{text-align:left;padding:10px 8px;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border);cursor:pointer;user-select:none}
    th:hover{color:var(--text);background:rgba(255,255,255,0.02)}
    td{padding:10px 8px;border-bottom:1px solid var(--border)}
    tr:last-child td{border-bottom:none}
    tr:hover{background:rgba(255,255,255,0.02)}

    .pill{display:inline-flex;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:700;border:1px solid transparent}
    .pill.ONLINE{background:rgba(5,46,22,0.5);border-color:#14532d;color:#4ade80}
    .pill.OFFLINE{background:rgba(59,10,10,0.5);border-color:#7f1d1d;color:#fca5a5}
    .pill.UNKNOWN{background:rgba(66,32,6,0.5);border-color:#713f12;color:#fde047}

    /* Bars */
    .bar-row{display:flex;align-items:center;gap:10px;font-size:13px}
    .bar-label{width:120px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .bar-track{flex:1;height:6px;background:#374151;border-radius:3px;overflow:hidden}
    .bar-fill{height:100%;border-radius:3px}
    .bar-val{width:50px;text-align:right;font-weight:600;font-feature-settings:"tnum"}

    .toggle-switch{display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;user-select:none}

    .loading-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(11,15,20,0.8);display:flex;align-items:center;justify-content:center;z-index:99;backdrop-filter:blur(2px)}
  </style>
</head>
<body>
  <div class="header">
    <h1>AssetIQ HQ Dashboard <span style="font-size:14px;color:var(--muted);font-weight:400;margin-left:8px">(Read-Only)</span></h1>
    <div>
      <button id="adminBtn" style="display:none" onclick="location.href='/hq/admin'">Admin Panel</button>
      <button class="danger" onclick="doLogout()">Logout</button>
    </div>
  </div>

  <div class="controls-bar">
    <div class="controls-group">
      <span class="muted">Date (UTC):</span>
      <input id="day" type="date" onchange="loadAll()"/>
      <button class="primary" onclick="loadAll()">Refresh Data</button>
    </div>
    <div class="controls-group">
      <label class="toggle-switch">
        <input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()">
        <span>Auto-Refresh (30s)</span>
      </label>
      <span id="status" class="muted" style="min-width:120px;text-align:right"></span>
    </div>
  </div>

  <div class="grid">
    <!-- Overview -->
    <div class="card" style="grid-column: span 2">
      <h2>All Plants Overview</h2>
      <div id="overview" style="overflow-x:auto"></div>
    </div>

    <!-- Downtime -->
    <div class="card">
      <h2>Downtime Comparison</h2>
      <div id="downtime"></div>
    </div>

    <!-- SLA -->
    <div class="card">
      <h2>SLA Breach Ranking</h2>
      <div id="sla"></div>
    </div>

    <!-- Top Reasons -->
    <div class="card" style="grid-column: span 2">
      <h2>Top Stop Reasons (Per Plant)</h2>
      <div id="reasons" class="grid" style="grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));gap:16px;border:none;padding:0"></div>
    </div>

    <!-- Insights -->
    <div class="card" style="grid-column: span 2">
      <h2>Phase-3 Intelligence Insights</h2>
      <div id="insights"></div>
    </div>
  </div>

<div id="loader" class="loading-overlay" style="display:none">
  <div style="color:var(--blue);font-weight:bold">Syncing Data...</div>
</div>

<script>
/*ROLES_INJECT*/
(function(){
  if (typeof USER_ROLES !== 'undefined' && USER_ROLES.includes('admin')) {
    const btn = document.getElementById('adminBtn');
    if(btn) btn.style.display = 'inline-block';
  }
})();

// -- State --
let refreshTimer = null;
let lastData = {};

function toggleAutoRefresh() {
  const on = document.getElementById("autoRefresh").checked;
  if(on) {
    loadAll();
    refreshTimer = setInterval(loadAll, 30000);
  } else {
    clearInterval(refreshTimer);
  }
}

async function doLogout(){
  await fetch("/hq/auth/logout", {method:"POST"});
  window.location.reload();
}

// -- Utils --
function esc(s){return String(s??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")}

// -- Renderers --
function renderTable(id, headers, rows, sortable=true){
  const el = document.getElementById(id);
  let h = '<table><thead><tr>';
  headers.forEach((hdr, idx) => {
    h += `<th onclick="sortTable('${id}', ${idx})">${esc(hdr)} ${sortable ? '↕' : ''}</th>`;
  });
  h += '</tr></thead><tbody>';

  if(rows.length === 0) {
    h += `<tr><td colspan="${headers.length}" style="text-align:center;color:var(--muted);padding:20px">No data available</td></tr>`;
  } else {
    for(const row of rows){
      h += '<tr>' + row.map(x => `<td>${x}</td>`).join('') + '</tr>';
    }
  }
  h += '</tbody></table>';
  el.innerHTML = h;
  el.dataset.rows = JSON.stringify(rows); // Store for sorting
}

function sortTable(id, colIdx) {
  const el = document.getElementById(id);
  if(!el.dataset.rows) return;

  let rows = JSON.parse(el.dataset.rows);
  let asc = el.dataset.asc === 'true';
  el.dataset.asc = !asc;

  rows.sort((a,b) => {
     // Strip HTML tags for comparison if needed, or assume raw data passed?
     // We stored HTML strings in rows, which is bad for sorting.
     // Improvement: We will just do a simple string comparison of the cell content.
     let va = String(a[colIdx]).replace(/<[^>]+>/g, '');
     let vb = String(b[colIdx]).replace(/<[^>]+>/g, '');

     // Try numeric
     let na = parseFloat(va.replace(/[^\d.-]/g, ''));
     let nb = parseFloat(vb.replace(/[^\d.-]/g, ''));

     if(!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
     return asc ? va.localeCompare(vb) : vb.localeCompare(va);
  });

  // Re-render body only to keep headers or full re-render
  // Check headers from DOM
  const ths = Array.from(el.querySelectorAll('th')).map(th => th.innerText.replace('↕','').trim());
  renderTable(id, ths, rows);
  el.dataset.asc = !asc; // Restore state after re-render
  el.dataset.rows = JSON.stringify(rows);
}

function renderBars(id, items, valKey, labelKey, color){
  const el = document.getElementById(id);
  if(!items || items.length === 0){
    el.innerHTML = '<div class="muted" style="text-align:center;padding:10px">No data</div>';
    return;
  }

  const max = Math.max(...items.map(i => i[valKey] || 0), 1);
  let h = '';
  for(const item of items){
    const val = item[valKey] || 0;
    const pct = (val / max) * 100;
    h += `
      <div class="bar-row" style="margin-bottom:8px">
        <div class="bar-label" title="${esc(item[labelKey])}">${esc(item[labelKey])}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div>
        <div class="bar-val">${val}</div>
      </div>
    `;
  }
  el.innerHTML = h;
}

// -- API --
async function api(path){
  const day=document.getElementById("day").value;
  const url = path.includes("?") ? `${path}&day_utc=${day}` : `${path}?day_utc=${day}`;
  const r = await fetch(url);
  if(r.status === 401) { window.location.reload(); return; }
  if(!r.ok) throw new Error(await r.text());
  return await r.json();
}

async function loadAll(){
  const status = document.getElementById("status");
  const loader = document.getElementById("loader");

  try{
    status.textContent = "Syncing...";
    // document.body.style.cursor = 'wait';

    // Overview
    const sum = await api('/hq/summary');
    const ovRows = sum.items.map(it => [
      `<span style="font-weight:600">${esc(it.display_name || it.site_code)}</span>`,
      `<span class="pill ${it.status}">${it.status}</span>`,
      it.updated_at_utc ? `<span title="${esc(it.updated_at_utc)}" style="cursor:help">Recently</span>` : '-',
      esc(it.downtime_minutes),
      esc(it.stops),
      esc(it.sla_breaches),
      `<span style="${it.critical_open_tickets > 0 ? 'color:#f87171;font-weight:bold' : ''}">${esc(it.critical_open_tickets)}</span> / ${esc(it.tickets_open)}`
    ]);
    renderTable("overview", ["Plant","Status","Last Sync","Downtime (min)","Stops","SLA Breaches","Critical / Open"], ovRows);

    // Downtime Bars
    const dt = await api('/hq/compare/downtime');
    renderBars("downtime", dt.items, "downtime_minutes", "display_name", "#eab308"); // yellow/orange

    // SLA Bars
    const sla = await api('/hq/rank/sla');
    renderBars("sla", sla.items, "sla_breaches", "display_name", "#ef4444"); // red

    // Reasons
    const rs = await api('/hq/top-reasons?limit=5');
    const rItems = rs.items || {};
    let rHtml = '';

    // Custom logic for reasons to use small tables inside cards
    const sites = Object.keys(rItems).sort();
    if(sites.length === 0){
        document.getElementById("reasons").innerHTML = '<div class="muted" style="padding:10px">No stop reasons reported.</div>';
    } else {
        // Build sub-cards
        for(const s of sites){
            const rows = rItems[s].map(x => [
                esc(x.reason_code),
                esc(x.stops),
                `<span style="color:#eab308;font-weight:600">${esc(x.downtime_minutes)}m</span>`
            ]);

            // Create mini table string
            let tbl = '<table style="margin-top:8px"><thead><tr><th style="font-size:11px">Reason</th><th style="font-size:11px;text-align:right">Stops</th><th style="font-size:11px;text-align:right">Time</th></tr></thead><tbody>';
            rows.forEach(r => tbl += `<tr><td>${r[0]}</td><td style="text-align:right">${r[1]}</td><td style="text-align:right">${r[2]}</td></tr>`);
            tbl += '</tbody></table>';

            rHtml += `
            <div style="background:#0b1220;padding:12px;border-radius:8px;border:1px solid #1f2937">
                <div style="font-weight:bold;color:#fff">${esc(s)}</div>
                ${tbl}
            </div>`;
        }
        document.getElementById("reasons").innerHTML = rHtml;
    }

    // Insights
    const ins = await api('/hq/insights');
    if(ins.items.length === 0) {
        document.getElementById("insights").innerHTML = '<div class="muted" style="padding:10px">No intelligence insights generated.</div>';
    } else {
        const insRows = ins.items.map(it => [
             `<span class="pill" style="background:${it.severity==='HIGH'?'#7f1d1d':(it.severity==='MEDIUM'?'#7c4a00':'#1f2937')};color:${it.severity==='HIGH'?'#fca5a5':(it.severity==='MEDIUM'?'#fde047':'#9ca3af')}">${it.severity}</span>`,
             `<span style="font-weight:600">${esc(it.display_name || it.site_code)}</span>`,
             esc(it.title),
             `<span style="font-size:12px;color:var(--muted)">${esc(it.detail?.note || '')}</span>`
        ]);
        renderTable("insights", ["Lev","Plant","Insight","Details"], insRows);
    }

    status.textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch(e) {
    status.textContent = "Error";
    console.error(e);
  } finally {
     // document.body.style.cursor = 'default';
  }
}

// Init
(function init(){
  const d=new Date();
  const iso = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())).toISOString().slice(0,10);
  document.getElementById("day").value=iso;
  loadAll();
})();
</script>
</body>
</html>"""


_ADMIN_HTML = r"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>HQ Admin - AssetIQ</title>
  <style>
    :root { color-scheme: dark; --bg: #0b0f14; --card: #111827; --border: #1f2937; --text: #e6edf3; --muted: #9ca3af; --blue: #2563eb; --blue-dim: #1d4ed8; }
    body{font-family:'Inter',system-ui,-apple-system,sans-serif;margin:0;background:var(--bg);color:var(--text);display:flex;justify-content:center;padding:40px;min-height:100vh}

    .container{max-width:800px;width:100%}
    .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
    h1{font-size:24px;margin:0;font-weight:700}

    .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:20px}
    .card h2{font-size:16px;margin:0 0 16px 0;color:var(--text);border-bottom:1px solid var(--border);padding-bottom:12px}

    /* Form */
    .form-grid{display:grid;gap:16px}
    .field label{display:block;font-size:12px;color:var(--muted);margin-bottom:6px;font-weight:500}
    input{width:100%;background:#0b1220;border:1px solid var(--border);color:var(--text);border-radius:6px;padding:10px;box-sizing:border-box;font-family:inherit}
    input:focus{outline:none;border-color:var(--blue)}

    /* Table */
    .table-container{overflow-x:auto;border:1px solid var(--border);border-radius:8px}
    table{width:100%;border-collapse:collapse;font-size:14px;background:#0b1220}
    th{text-align:left;padding:12px 16px;color:var(--muted);background:var(--card);border-bottom:1px solid var(--border);font-weight:600}
    td{padding:12px 16px;border-bottom:1px solid var(--border)}
    tr:last-child td{border-bottom:none}

    /* Buttons */
    .btn{background:var(--card);border:1px solid var(--border);color:var(--text);padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:500;transition:all 0.2s}
    .btn:hover{background:var(--border)}
    .btn-primary{background:var(--blue);border-color:var(--blue);color:white}
    .btn-primary:hover{background:var(--blue-dim)}
    .btn-danger{background:rgba(220,38,38,0.1);color:#fca5a5;border-color:rgba(220,38,38,0.3)}
    .btn-danger:hover{background:rgba(220,38,38,0.2)}
    .btn-sm{padding:4px 8px;font-size:12px}

    /* Modal */
    .modal-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:99;backdrop-filter:blur(2px)}
    .modal{background:var(--card);border:1px solid var(--border);width:90%;max-width:400px;border-radius:12px;padding:24px;box-shadow:0 10px 25px rgba(0,0,0,0.5)}

    .status-msg{margin-top:10px;font-size:13px;padding:10px;border-radius:6px;display:none}
    .success{background:rgba(52,211,153,0.1);color:#34d399;border:1px solid rgba(52,211,153,0.2)}
    .error{background:rgba(248,113,113,0.1);color:#f87171;border:1px solid rgba(248,113,113,0.2)}

    .muted-text{color:var(--muted);font-size:12px}
  </style>
</head>
<body>

<div class="container">
  <div class="header">
    <h1>HQ Administration</h1>
    <button class="btn" onclick="location.href='/hq/ui'">← Back to Dashboard</button>
  </div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2 style="border:none;margin:0;padding:0">User Management</h2>
      <button class="btn btn-primary" onclick="showCreateModal()">+ Create User</button>
    </div>

    <div class="table-container">
      <table id="userTable">
        <thead>
          <tr>
            <th>Username</th>
            <th>Roles</th>
            <th>Type</th>
            <th style="text-align:right">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr><td colspan="4" style="text-align:center;padding:20px;color:var(--muted)">Loading users...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- Create User Modal -->
<div id="createModal" class="modal-overlay" style="display:none">
  <div class="modal">
    <h2 style="border:none;margin-top:0">Create New User</h2>
    <div class="form-grid">
      <div class="field">
        <label>Username</label>
        <input id="newUsername" type="text" placeholder="e.g. supervisor_01" autofocus>
      </div>
      <div class="field">
        <label>PIN Code (min 6 digits)</label>
        <input id="newPin" type="number" placeholder="123456">
      </div>
      <div class="field">
        <label>Roles</label>
        <select id="newRoles" style="width:100%;padding:10px;background:#0b1220;border:1px solid var(--border);color:var(--text);border-radius:6px">
          <option value="user">User (Read-Only)</option>
          <option value="admin">Admin (Full Access)</option>
        </select>
        <div class="muted-text" style="margin-top:4px">Admins can create/delete users.</div>
      </div>

      <div id="createMsg" class="status-msg"></div>

      <div style="display:flex;gap:10px;margin-top:10px">
        <button class="btn btn-primary" style="flex:1" onclick="doCreate()">Create User</button>
        <button class="btn" style="flex:1" onclick="closeModal()">Cancel</button>
      </div>
    </div>
  </div>
</div>

<script>
async function api(path, method="GET", body=null){
  const opts = {method, headers:{"Content-Type":"application/json"}};
  if(body) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  if(r.status === 401) { location.href="/hq/ui"; return; }
  const data = await r.json();
  if(!r.ok) throw new Error(data.detail || "Request failed");
  return data;
}

// -- Load --
async function loadUsers(){
  const tbody = document.querySelector("#userTable tbody");
  try{
    const res = await api("/hq/auth/users");
    if(!res.items || res.items.length === 0){
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--muted)">No users found.</td></tr>';
        return;
    }

    tbody.innerHTML = res.items.map(u => {
      const isMe = false; // TODO: could verify against current user token if needed, but backend blocks delete anyway
      return `
        <tr>
          <td style="font-weight:500;color:white">${esc(u.username)}</td>
          <td>${esc(u.roles)}</td>
          <td>${u.roles.includes('admin') ? '<span style="color:#60a5fa">Admin</span>' : '<span style="color:#9ca3af">Standard</span>'}</td>
          <td style="text-align:right">
             <button class="btn btn-danger btn-sm" onclick="doDelete('${esc(u.username)}')" title="Delete User">Delete</button>
          </td>
        </tr>
      `;
    }).join("");
  } catch(e){
    tbody.innerHTML = `<tr><td colspan="4" style="color:#f87171;text-align:center">${e.message}</td></tr>`;
  }
}

// -- Actions --
function showCreateModal(){
  document.getElementById("createModal").style.display = "flex";
  document.getElementById("newUsername").value = "";
  document.getElementById("newPin").value = "";
  document.getElementById("createMsg").style.display = "none";
  setTimeout(()=>document.getElementById("newUsername").focus(), 50);
}
function closeModal(){
  document.getElementById("createModal").style.display = "none";
}

async function doCreate(){
   const username = document.getElementById("newUsername").value.trim();
   const pin = document.getElementById("newPin").value.trim();
   const roles = document.getElementById("newRoles").value;
   const msgBox = document.getElementById("createMsg");

   msgBox.style.display="none";
   if(!username || !pin) return showError("All fields required");

   try{
     await api("/hq/auth/create-user", "POST", {username, pin, roles});
     closeModal();
     loadUsers();
   } catch(e){
     showError(e.message);
   }
}

function showError(msg){
  const el = document.getElementById("createMsg");
  el.textContent = msg;
  el.className = "status-msg error";
  el.style.display = "block";
}

async function doDelete(username){
  if(!confirm(`Are you sure you want to permanently delete user '${username}'?`)) return;
  try{
    await api(`/hq/auth/users/${username}`, "DELETE");
    loadUsers();
  } catch(e){
    alert("Delete failed: " + e.message);
  }
}

function esc(s){return String(s||"").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");}

// Init
loadUsers();

// Close modal on outside click
document.getElementById("createModal").addEventListener("click", e => {
    if(e.target === document.getElementById("createModal")) closeModal();
});
</script>
</body>
</html>"""

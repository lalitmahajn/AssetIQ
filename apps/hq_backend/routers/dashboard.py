from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, desc

from common_core.db import HQSessionLocal
from common_core.security import verify_jwt
from apps.hq_backend.models import PlantRegistry, RollupDaily, TicketSnapshot, StopReasonDaily

router = APIRouter(prefix="/hq", tags=["hq-dashboard"])


def _get_current_user(request: Request) -> Dict[str, Any]:
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
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")


def _today_utc() -> str:
    return datetime.utcnow().date().isoformat()


@router.get("/plants")
def plants(user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
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
                    "last_seen_at_utc": p.last_seen_at_utc.isoformat() if p.last_seen_at_utc else None,
                }
            )
        return {"items": items}
    finally:
        db.close()


@router.get("/summary")
def summary(day_utc: Optional[str] = None, user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
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
        items: List[Dict[str, Any]] = []
        now = datetime.utcnow()
        for p in plants:
            r = by_site.get(p.site_code)
            # status heuristic: stale if last seen > 15 min
            status = "UNKNOWN"
            if p.last_seen_at_utc:
                delta = now - p.last_seen_at_utc
                if delta <= timedelta(minutes=15):
                    status = "ONLINE"
                else:
                    status = "OFFLINE"
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
                    "updated_at_utc": r.updated_at_utc.isoformat() if (r and r.updated_at_utc) else None,
                    "last_seen_at_utc": p.last_seen_at_utc.isoformat() if p.last_seen_at_utc else None,
                }
            )
        return {"day_utc": day, "items": items}
    finally:
        db.close()


@router.get("/compare/downtime")
def compare_downtime(day_utc: Optional[str] = None, user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
    day = (day_utc or _today_utc())[:10]
    db = HQSessionLocal()
    try:
        rows = db.execute(
            select(RollupDaily.site_code, RollupDaily.downtime_minutes)
            .where(RollupDaily.day_utc == day)
            .order_by(desc(RollupDaily.downtime_minutes))
        ).all()
        items = [{"site_code": r[0], "downtime_minutes": int(r[1] or 0)} for r in rows]
        return {"day_utc": day, "items": items}
    finally:
        db.close()


@router.get("/rank/sla")
def rank_sla(day_utc: Optional[str] = None, user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
    day = (day_utc or _today_utc())[:10]
    db = HQSessionLocal()
    try:
        rows = db.execute(
            select(RollupDaily.site_code, RollupDaily.sla_breaches)
            .where(RollupDaily.day_utc == day)
            .order_by(desc(RollupDaily.sla_breaches))
        ).all()
        items = [{"site_code": r[0], "sla_breaches": int(r[1] or 0)} for r in rows]
        return {"day_utc": day, "items": items}
    finally:
        db.close()


@router.get("/top-reasons")
def top_reasons(day_utc: Optional[str] = None, limit: int = 5, user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
    day = (day_utc or _today_utc())[:10]
    limit = max(1, min(int(limit), 20))
    db = HQSessionLocal()
    try:
        rows = db.execute(
            select(StopReasonDaily.site_code, StopReasonDaily.reason_code, StopReasonDaily.stops, StopReasonDaily.downtime_minutes)
            .where(StopReasonDaily.day_utc == day)
            .order_by(desc(StopReasonDaily.downtime_minutes))
        ).all()
        # group
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for site_code, reason_code, stops, dtm in rows:
            grouped.setdefault(site_code, [])
            if len(grouped[site_code]) < limit:
                grouped[site_code].append(
                    {"reason_code": reason_code, "stops": int(stops or 0), "downtime_minutes": int(dtm or 0)}
                )
        return {"day_utc": day, "limit": limit, "items": grouped}
    finally:
        db.close()


@router.get("/insights")
def insights(day_utc: Optional[str] = None, user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
    day = (day_utc or _today_utc())[:10]
    db = HQSessionLocal()
    try:
        from apps.hq_backend.models import InsightDaily
        rows = db.execute(
            select(InsightDaily)
            .where(InsightDaily.day_utc == day)
            .order_by(desc(InsightDaily.severity), InsightDaily.id)
        ).scalars().all()
        
        items = []
        for r in rows:
            items.append({
                "site_code": r.site_code or "GLOBAL",
                "type": r.insight_type,
                "title": r.title,
                "severity": r.severity,
                "detail": r.detail_json
            })
        return {"day_utc": day, "items": items}
    finally:
        db.close()


@router.get("/admin", response_class=HTMLResponse)
def admin(user: Dict[str, Any] = Depends(_get_current_user)) -> Response:
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


_DASHBOARD_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>AssetIQ HQ Dashboard</title>
  <style>
    body{font-family:Arial,Helvetica,sans-serif;margin:16px;background:#0b0f14;color:#e6edf3}
    .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
    h1{font-size:20px;margin:0}
    .row{display:flex;gap:12px;flex-wrap:wrap}
    .card{background:#111827;border:1px solid #1f2937;border-radius:10px;padding:12px;min-width:260px;flex:1}
    .muted{color:#9ca3af;font-size:12px}
    table{width:100%;border-collapse:collapse;margin-top:8px}
    th,td{padding:6px;border-bottom:1px solid #1f2937;font-size:13px;text-align:left}
    .pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid #374151}
    .ok{background:#052e16;border-color:#14532d}
    .warn{background:#3f2a00;border-color:#7c4a00}
    .bad{background:#3b0a0a;border-color:#7f1d1d}
    .sev-HIGH{background:#3b0a0a;border-color:#7f1d1d;color:#fca5a5}
    .sev-MEDIUM{background:#3f2a00;border-color:#7c4a00;color:#fde047}
    .sev-LOW{background:#1f2937;border-color:#374151;color:#9ca3af}
    .controls{display:flex;gap:8px;align-items:center;margin-bottom:10px}
    input{background:#0b1220;border:1px solid #1f2937;color:#e6edf3;border-radius:8px;padding:6px 8px;color-scheme:dark}
    input::-webkit-calendar-picker-indicator{cursor:pointer}
    button{background:#1f2937;border:1px solid #374151;color:#e6edf3;border-radius:8px;padding:6px 10px;cursor:pointer}
    button:hover{background:#243244}
    .logout-btn{background:#3b0a0a;border-color:#7f1d1d}
    .logout-btn:hover{background:#7f1d1d}
    .admin-btn{background:#4b5563;border:1px solid #374151;color:#e6edf3;border-radius:8px;padding:6px 10px;cursor:pointer;margin-right:8px}
    .admin-btn:hover{background:#6b7280}
  </style>
</head>
<body>
  <div class="header">
    <h1>AssetIQ HQ Dashboard (Read-Only)</h1>
    <div>
      <button id="adminBtn" class="admin-btn" style="display:none" onclick="location.href='/hq/admin'">Admin</button>
      <button class="logout-btn" onclick="doLogout()">Logout</button>
    </div>
  </div>
  <div class="controls">
    <span class="muted">Day (UTC):</span>
    <input id="day" type="date"/>
    <button onclick="loadAll()">Refresh</button>
    <span class="muted" id="status"></span>
  </div>

  <div class="row">
    <div class="card">
      <div class="muted">All Plants Overview</div>
      <div id="overview"></div>
    </div>
    <div class="card">
      <div class="muted">Downtime Comparison</div>
      <div id="downtime"></div>
    </div>
  </div>

  <div class="row" style="margin-top:12px">
    <div class="card">
      <div class="muted">SLA Breach Ranking</div>
      <div id="sla"></div>
    </div>
    <div class="card">
      <div class="muted">Top Stop Reasons (per plant)</div>
      <div id="reasons"></div>
    </div>
  </div>
  
  <div class="row" style="margin-top:12px">
    <div class="card" style="flex:2">
      <div class="muted">Phase-3 Intelligence Insights</div>
      <div id="insights"></div>
    </div>
  </div>

<script>
/*ROLES_INJECT*/
(function(){
  if (typeof USER_ROLES !== 'undefined' && USER_ROLES.includes('admin')) {
    const btn = document.getElementById('adminBtn');
    if(btn) btn.style.display = 'inline-block';
  }
})();
function esc(s){return String(s??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")}
async function doLogout(){
  await fetch("/hq/auth/logout", {method:"POST"});
  window.location.reload();
}
function pill(status){
  if(status==="ONLINE") return '<span class="pill ok">ONLINE</span>'
  if(status==="OFFLINE") return '<span class="pill bad">OFFLINE</span>'
  return '<span class="pill warn">UNKNOWN</span>'
}
function sev(s){
    return `<span class="pill sev-${s}">${s}</span>`
}
async function api(path){
  const day=document.getElementById("day").value
  const url = path.includes("?") ? `${path}&day_utc=${encodeURIComponent(day)}` : `${path}?day_utc=${encodeURIComponent(day)}`
  const r = await fetch(url)
  if(r.status === 401) {
    window.location.reload();
    return;
  }
  if(!r.ok) throw new Error(await r.text())
  return await r.json()
}
function table(headers, rows){
  let h='<table><thead><tr>'+headers.map(x=>`<th>${esc(x)}</th>`).join('')+'</tr></thead><tbody>'
  for(const row of rows){
    h+='<tr>'+row.map(x=>`<td>${x}</td>`).join('')+'</tr>'
  }
  h+='</tbody></table>'
  return h
}
async function loadAll(){
  try{
    document.getElementById("status").textContent="Loading..."
    const day=document.getElementById("day").value
    const sum = await api('/hq/summary')
    const ovRows = sum.items.map(it=>[
      esc(it.site_code),
      pill(it.status),
      esc(it.downtime_minutes),
      esc(it.stops),
      esc(it.sla_breaches),
      esc(it.tickets_open),
      esc(it.critical_open_tickets),
    ])
    document.getElementById("overview").innerHTML = table(
      ["Plant","Status","Downtime(min)","Stops","SLA Breaches","Tickets Open","Critical Open"],
      ovRows
    )

    const dt = await api('/hq/compare/downtime')
    const dtRows = dt.items.map(it=>[esc(it.site_code), esc(it.downtime_minutes)])
    document.getElementById("downtime").innerHTML = table(["Plant","Downtime(min)"], dtRows)

    const sla = await api('/hq/rank/sla')
    const slaRows = sla.items.map(it=>[esc(it.site_code), esc(it.sla_breaches)])
    document.getElementById("sla").innerHTML = table(["Plant","SLA Breaches"], slaRows)

    const rs = await api('/hq/top-reasons?limit=5')
    let html=''
    const items = rs.items || {}
    const sites = Object.keys(items).sort()
    if(sites.length===0){
      html='<div class="muted">No stop reason aggregates received yet.</div>'
    }else{
      for(const s of sites){
        const rows = items[s].map(x=>[esc(x.reason_code), esc(x.stops), esc(x.downtime_minutes)])
        html += `<div style="margin-top:10px"><div><b>${esc(s)}</b></div>${table(["Reason","Stops","Downtime(min)"], rows)}</div>`
      }
    }
    document.getElementById("reasons").innerHTML = html
    
    // Insights
    const ins = await api('/hq/insights')
    if(ins.items.length === 0) {
        document.getElementById("insights").innerHTML = '<div class="muted" style="padding:10px">No intelligence insights generated for this day.</div>'
    } else {
        const insRows = ins.items.map(it => [
            sev(it.severity),
            esc(it.site_code),
            esc(it.title),
            formatDetail(it.detail)
        ])
        document.getElementById("insights").innerHTML = table(["Severity", "Plant", "Insight", "Details"], insRows)
    }

    document.getElementById("status").textContent=`Updated for ${day}`
  }catch(e){
    document.getElementById("status").textContent="Error: "+e.message
  }
}

function formatDetail(d) {
    if (!d) return "";
    let h = "";
    
    if (d.top && Array.isArray(d.top) && d.top.length > 0) {
        h += '<div style="margin-top:4px"><span class="muted">Top Contributors:</span><ul style="margin:2px 0 0 0;padding-left:20px;color:#d1d5db">';
        for (const item of d.top) {
            const parts = [];
            let main = "";
            for (const [k,v] of Object.entries(item)) {
                if (k === 'site_code' || k === 'reason_code') {
                    main = `<span style="color:#e6edf3;font-weight:600">${esc(v)}</span>`;
                } else if (k === 'downtime_minutes') {
                   parts.push(`${esc(v)} min`);
                } else if (k === 'stops') {
                   parts.push(`${esc(v)} stops`);
                } else if (k === 'sla_breaches') {
                   parts.push(`${esc(v)} breaches`);
                } else {
                   parts.push(`${k.replace(/_/g,' ')}: ${esc(v)}`);
                }
            }
            let line = main ? `${main} <span class="muted">(${parts.join(', ')})</span>` : parts.join(', ');
            h += `<li style="font-size:12px;margin-bottom:3px;line-height:1.4">${line}</li>`;
        }
        h += '</ul></div>';
    }
    
    if (d.window_days) h += `<div class="muted" style="margin-top:4px;font-size:11px">Analysis Window: ${esc(d.window_days)} days</div>`;
    if (d.note) h += `<div style="margin-top:4px;font-style:italic;color:#6b7280;font-size:11px">${esc(d.note)}</div>`;
    
    // Fallback if structure is unknown
    if (!d.note && !d.top && !d.window_days) {
        h += `<pre style="margin:0;font-size:11px;color:#9ca3af">${esc(JSON.stringify(d, null, 2))}</pre>`;
    }
    return h;
}
(function init(){
  const d=new Date()
  const iso = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())).toISOString().slice(0,10)
  document.getElementById("day").value=iso
  loadAll()
})()
</script>
</body>
</html>"""


_ADMIN_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>HQ Admin - AssetIQ</title>
  <style>
    body{font-family:Arial,Helvetica,sans-serif;margin:0;background:#0b0f14;color:#e6edf3;display:flex;align-items:center;justify-content:center;height:100vh}
    .card{background:#111827;border:1px solid #1f2937;border-radius:10px;padding:24px;width:360px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.1),0 2px 4px -1px rgba(0,0,0,0.06)}
    h1{font-size:20px;margin:0 0 20px 0;text-align:center}
    .field{margin-bottom:16px}
    label{display:block;font-size:12px;color:#9ca3af;margin-bottom:4px}
    input{width:100%;background:#0b1220;border:1px solid #1f2937;color:#e6edf3;border-radius:8px;padding:8px;box-sizing:border-box}
    button{width:100%;background:#2563eb;border:none;color:white;border-radius:8px;padding:10px;cursor:pointer;font-weight:bold;margin-top:12px}
    button:hover{background:#1d4ed8}
    .cancel{background:#374151;margin-top:8px}
    .cancel:hover{background:#4b5563}
    .error{color:#f87171;font-size:12px;margin-top:12px;text-align:center;display:none}
    .success{color:#34d399;font-size:12px;margin-top:12px;text-align:center;display:none}
  </style>
</head>
<body>
  <div class="card">
    <h1>Create HQ User</h1>
    <div class="field">
      <label>Username</label>
      <input id="username" type="text" placeholder="e.g. operator"/>
    </div>
    <div class="field">
      <label>PIN (min 6 digits)</label>
      <input id="pin" type="password" placeholder="123456"/>
    </div>
    <div class="field">
      <label>Roles (comma separated)</label>
      <input id="roles" type="text" value="user" placeholder="admin, user"/>
    </div>
    <button onclick="doCreate()">Create User</button>
    <button class="cancel" onclick="location.href='/hq/ui'">Back to Dashboard</button>
    <div id="error" class="error"></div>
    <div id="success" class="success"></div>
  </div>
  <script>
    async function doCreate(){
      const username = document.getElementById("username").value.trim();
      const pin = document.getElementById("pin").value.trim();
      const roles = document.getElementById("roles").value;
      
      const err = document.getElementById("error");
      const succ = document.getElementById("success");
      err.style.display = "none";
      succ.style.display = "none";
      
      if(!username || !pin){
        err.textContent = "Username and PIN are required";
        err.style.display = "block";
        return;
      }
      
      try {
        const r = await fetch("/hq/auth/create-user", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({username, pin, roles})
        });
        if (r.status === 401) {
             window.location.href = "/hq/ui"; // Redirect to login page handler
             return;
        }
        if (!r.ok) {
          const detail = await r.json();
          throw new Error(detail.detail || "Creation failed");
        }
        succ.textContent = `User '${username}' created successfully!`;
        succ.style.display = "block";
        document.getElementById("username").value = "";
        document.getElementById("pin").value = "";
      } catch (e) {
        err.textContent = e.message;
        err.style.display = "block";
      }
    }
  </script>
</body>
</html>"""

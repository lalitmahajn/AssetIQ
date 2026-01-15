from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, desc

from common_core.db import HQSessionLocal
from apps.hq_backend.models import PlantRegistry, RollupDaily, TicketSnapshot, StopReasonDaily

router = APIRouter(prefix="/hq", tags=["hq-dashboard"])


def _today_utc() -> str:
    return datetime.utcnow().date().isoformat()


@router.get("/plants")
def plants() -> Dict[str, Any]:
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
def summary(day_utc: Optional[str] = None) -> Dict[str, Any]:
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
def compare_downtime(day_utc: Optional[str] = None) -> Dict[str, Any]:
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
def rank_sla(day_utc: Optional[str] = None) -> Dict[str, Any]:
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
def top_reasons(day_utc: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
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
def insights(day_utc: Optional[str] = None) -> Dict[str, Any]:
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


@router.get("/ui", response_class=HTMLResponse)
def ui() -> str:
    # minimal, no-build UI for management (read-only)
    return _DASHBOARD_HTML


_DASHBOARD_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>AssetIQ HQ Dashboard</title>
  <style>
    body{font-family:Arial,Helvetica,sans-serif;margin:16px;background:#0b0f14;color:#e6edf3}
    h1{font-size:20px;margin:0 0 12px 0}
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
  </style>
</head>
<body>
  <h1>AssetIQ HQ Dashboard (Read-Only)</h1>
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
function esc(s){return String(s??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")}
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

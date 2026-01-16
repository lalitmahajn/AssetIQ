from __future__ import annotations
import os
import sys
import random
import uuid
import hmac
import hashlib
import json
import httpx
from datetime import datetime, timedelta

# Ensure we can import from the project root
sys.path.append(os.getcwd())

from common_core.db import PlantSessionLocal
from common_core.config import settings
from apps.plant_backend.models import Asset, MasterType, MasterItem, StopQueue, Ticket, ReportRequest, AuditLog
from apps.plant_backend import services

def _now():
    return datetime.utcnow()

def sign_payload(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

def sync_to_hq(items: list):
    if not settings.hq_receiver_url:
        print("Skipping HQ sync: HQ_RECEIVER_URL not set.")
        return
    
    payload = {"items": items}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = sign_payload(payload_bytes, settings.sync_hmac_secret)
    
    try:
        resp = httpx.post(
            settings.hq_receiver_url,
            content=payload_bytes,
            headers={"X-Signature": sig, "Content-Type": "application/json"},
            timeout=10
        )
        if resp.status_code == 200:
            print(f" Successfully synced {len(items)} items to HQ: {resp.json()}")
        else:
            print(f" HQ Sync Failed (HTTP {resp.status_code}): {resp.text}")
    except Exception as e:
        print(f" HQ Sync Error: {e}")

def simulate():
    db = PlantSessionLocal()
    print(f"Starting simulation for site: {settings.plant_site_code}")
    
    try:
        # 1. Ensure Assets Exist
        assets = db.query(Asset).all()
        if not assets:
            print("No assets found. Creating polymer plant assets with hierarchy...")
            # 1. Create Parent Area
            # Note: We keep ID and Asset Code identical to match the Admin Hierarchy UI behavior
            parent_area = {"id": "HALL-A", "asset_code": "HALL-A", "name": "Polymer Production Hall A", "category": "Area", "criticality": "high"}
            services.asset_create(db, parent_area, actor_user_id="admin", request_id=None)
            db.flush()

            # 2. Create Children Assets
            demo_assets = [
                {"id": "R-101", "asset_code": "R-101", "name": "Polymerization Reactor A", "category": "Reaction", "criticality": "high", "parent_id": "HALL-A"},
                {"id": "EX-201", "asset_code": "EX-201", "name": "Twin-Screw Extruder", "category": "Extrusion", "criticality": "high", "parent_id": "HALL-A"},
                {"id": "C-301", "asset_code": "C-301", "name": "High-Speed Centrifuge", "category": "Separation", "criticality": "medium", "parent_id": "HALL-A"},
                {"id": "D-401", "asset_code": "D-401", "name": "Fluid Bed Dryer", "category": "Drying", "criticality": "medium", "parent_id": "HALL-A"},
                {"id": "COL-501", "asset_code": "COL-501", "name": "Distillation Column", "category": "Distillation", "criticality": "high", "parent_id": "HALL-A"},
            ]
            for a_data in demo_assets:
                services.asset_create(db, a_data, actor_user_id="admin", request_id=None)
            db.commit()
            assets = db.query(Asset).all()
        
        asset_ids = [a.id for a in assets if a.category != "Area"]
        print(f"Generating data for machines: {asset_ids}")

        # 2. Ensure Master Data Exist (Stop Reasons)
        reasons = [
            "Pressure Deviation", "Temperature Unstable", "Catalyst Change", 
            "Filter Clogging", "Raw Material Impurity", "Pump Cavitation",
            "Reactor Cleaning", "Power Outage", "Safety Valve Trip"
        ]
        
        # Check if master type exists
        mt = db.query(MasterType).filter_by(type_code="STOP_REASON").first()
        if not mt:
            mt = MasterType(
                site_code=settings.plant_site_code,
                type_code="STOP_REASON",
                name="Stop Reason",
                is_active=True,
                created_at_utc=_now()
            )
            db.add(mt)
            db.flush()
        
        for r_name in reasons:
            item_code = r_name.upper().replace(" ", "_")
            exists = db.query(MasterItem).filter_by(master_type_code="STOP_REASON", item_code=item_code).first()
            if not exists:
                services.master_item_create(db, "STOP_REASON", item_code, r_name, actor_id="admin")
        db.commit()

        # 3. Generate Historical Data (Past 30 Days)
        print("Generating historical stops for efficiency analysis...")
        yesterday = _now() - timedelta(days=1)
        start_date = yesterday - timedelta(days=30)
        
        # Clean current data to avoid mess for demo (Optional - user might want to keep)
        # db.query(StopQueue).delete()
        # db.query(Ticket).delete()
        
        # Define performance profiles for assets to create a colorful UI (Red/Yellow/Green)
        # CRITICAL (<75%): Reactor - The "Problem" machine
        # WARNING (75-90%): Distillation Column
        # HEALTHY (>90%): Extruder, Centrifuge, Dryer
        asset_profiles = {
            "R-101": {"max_stops": 8, "min_dur": 100, "max_dur": 240},  # Aggressive: Will be RED (<70%)
            "COL-501": {"max_stops": 4, "min_dur": 45, "max_dur": 150}, # Moderate: Will be YELLOW (70-90%)
            "EX-201": {"max_stops": 2, "min_dur": 5, "max_dur": 45},     # Efficient: Will be GREEN (>90%)
            "D-401": {"max_stops": 2, "min_dur": 5, "max_dur": 45},      # Efficient: Will be GREEN (>90%)
            "C-301": {"max_stops": 1, "min_dur": 5, "max_dur": 30},      # Efficient: Will be GREEN (>90%)
        }

        current_date = start_date
        while current_date <= yesterday:
            day_str = current_date.strftime("%Y-%m-%d")
            day_stops = 0
            day_downtime = 0
            reason_map = {} # reason -> (count, downtime)
            
            # For each day, create some stops for each asset
            for asset_id in asset_ids:
                profile = asset_profiles.get(asset_id, {"max_stops": 2, "min_dur": 5, "max_dur": 60})
                
                num_stops = random.randint(1, profile["max_stops"])
                for _ in range(num_stops):
                    # Random time during the day
                    hour = random.randint(0, 23)
                    minute = random.randint(0, 59)
                    stop_start = current_date.replace(hour=hour, minute=minute)
                    
                    duration_min = random.randint(profile["min_dur"], profile["max_dur"])
                    stop_end = stop_start + timedelta(minutes=duration_min)
                    
                    reason = random.choice(reasons)
                    
                    # Create Stop
                    res = services.open_stop(db, asset_id, reason, "admin", None, None)
                    db.flush() # Ensure objects are in session state for retrieval
                    
                    stop_id = res["stop_id"]
                    ticket_id = res["ticket_id"]
                    
                    # Adjust times to historical
                    sq = db.get(StopQueue, stop_id)
                    if sq:
                        sq.opened_at_utc = stop_start
                        sq.closed_at_utc = stop_end
                        sq.is_open = False
                        sq.resolution_text = f"Fixed: {reason} resolved."
                    
                    tck = db.get(Ticket, ticket_id)
                    if tck:
                        tck.created_at_utc = stop_start
                        tck.status = "CLOSED"
                        tck.resolved_at_utc = stop_end
                        tck.close_note = "Problem resolved by maintenance."
                    
                    # Update Timeline Events created by services
                    # Note: timeline_events table has occurred_at_utc
                    from apps.plant_backend.models import TimelineEvent
                    te_list = db.query(TimelineEvent).filter(TimelineEvent.correlation_id.in_([f"stop_open:{stop_id}", f"ticket_open:{ticket_id}"])).all()
                    for te in te_list:
                        te.occurred_at_utc = stop_start
                        te.created_at_utc = stop_start
                    
                    # Backdate Audit Logs so "Audit Logs" page looks rich
                    audit_entries = db.query(AuditLog).filter(
                        AuditLog.entity_id.in_([stop_id, ticket_id])
                    ).all()
                    for entry in audit_entries:
                        entry.created_at_utc = stop_start
            
                    
                    # Track for HQ Rollup
                    day_stops += 1
                    day_downtime += duration_min
                    r_count, r_min = reason_map.get(reason, (0, 0))
                    reason_map[reason] = (r_count + 1, r_min + duration_min)
            
            # Send Daily Rollup to HQ
            hq_items = []
            stop_reasons = []
            for r_code, (count, d_min) in reason_map.items():
                stop_reasons.append({"reason_code": r_code, "stops": count, "downtime_minutes": d_min})
            
            rollup_payload = {
                "day_utc": day_str,
                "stops": day_stops,
                "downtime_minutes": day_downtime,
                "tickets_open": 0,
                "faults": day_stops,
                "stop_reasons": stop_reasons
            }
            hq_items.append({
                "site_code": settings.plant_site_code,
                "entity_type": "rollup",
                "entity_id": day_str,
                "payload": rollup_payload,
                "correlation_id": f"sim_rollup:{settings.plant_site_code}:{day_str}"
            })
            sync_to_hq(hq_items)

            print(f" Generated data for {current_date.date()}")
            current_date += timedelta(days=1)
            db.commit()

        # 4. Generate Open Stops (For today)
        print("Creating active stops for real-time demo...")
        hq_tickets = []
        for i in range(2):
            asset_id = asset_ids[i % len(asset_ids)]
            reason = random.choice(reasons)
            res = services.open_stop(db, asset_id, f"[URGENT] {reason}", "admin", None, None)
            
            # Prepare ticket sync for HQ
            ticket_id = res["ticket_id"]
            db.flush()
            t = db.get(Ticket, ticket_id)
            if t:
                hq_tickets.append({
                    "site_code": settings.plant_site_code,
                    "entity_type": "ticket",
                    "entity_id": ticket_id,
                    "payload": {
                        "asset_id": t.asset_id,
                        "title": t.title,
                        "status": t.status,
                        "priority": t.priority,
                        "created_at_utc": t.created_at_utc.isoformat() + "Z",
                        "sla_due_at_utc": t.sla_due_at_utc.isoformat() + "Z" if t.sla_due_at_utc else None
                    },
                    "correlation_id": f"sim_ticket:{ticket_id}"
                })
        
        if hq_tickets:
            sync_to_hq(hq_tickets)
            
        db.commit()

        # 5. Send one final heartbeat so HQ shows Plant as ONLINE
        print("Sending heartbeat to HQ...")
        sync_to_hq([{
            "site_code": settings.plant_site_code,
            "entity_type": "heartbeat", # Unknown type triggers _upsert_plant in HQ
            "entity_id": "heartbeat",
            "payload": {},
            "correlation_id": f"heartbeat:{uuid.uuid4().hex}"
        }])

        # 6. Generate a sample report
        print("Generating a sample downtime report...")
        report_start = (yesterday - timedelta(days=7)).isoformat()
        report_end = _now().isoformat()
        services.report_request_create_and_generate_csv(
            db,
            report_type="downtime_by_asset",
            date_from=report_start,
            date_to=report_end,
            filters={},
            actor_user_id="admin",
            actor_station_code=None,
            request_id=None
        )
        db.commit()

        print("\nSUCCESS: Demo simulation complete!")
        print("- 30 days of historical data generated.")
        print("- Active stops created.")
        print("- Sample report generated in Vault.")
        print("- You can now show Plant Efficiency, Stop Queue, and Reports features.")

    except Exception as e:
        db.rollback()
        print(f"ERROR during simulation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    simulate()

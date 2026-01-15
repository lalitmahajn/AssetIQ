
import csv
import logging
import sys
from datetime import datetime
from sqlalchemy import select

from common_core.db import PlantSessionLocal
from apps.plant_backend.models import StopQueue, TimelineEvent, Asset
from apps.plant_backend.services import _new_id

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sim_csv")

CSV_PATH = "/app/Copy of Asset Management System - ✦ Status of Instrument.csv"

def parse_date(date_str):
    if not date_str:
        return datetime.utcnow()
    try:
        # Format: 8/29/2025 15:31:29
        return datetime.strptime(date_str, "%m/%d/%Y %H:%M:%S")
    except ValueError:
        try:
             # Try without seconds just in case
             return datetime.strptime(date_str, "%m/%d/%Y %H:%M")
        except:
            log.warning(f"Could not parse date: {date_str}, using now")
            return datetime.utcnow()

def simulate():
    db = PlantSessionLocal()
    try:
        log.info(f"Reading CSV from: {CSV_PATH}")
        with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        log.info(f"Found {len(rows)} rows.")
        
        if rows:
            log.info(f"CSV Keys: {list(rows[0].keys())}")
        
        # 1. Unique Assets Check & Creation
        unique_assets = {}
        for row in rows:
            asset_id = row.get("Asset ID")
            asset_name = row.get("Asset Name")
            if asset_id and asset_name:
                unique_assets[asset_id] = asset_name
                
        for asset_id, asset_name in unique_assets.items():
            # Check if exists
            existing = db.execute(select(Asset).where(Asset.id == asset_id)).scalar_one_or_none()
            if not existing:
                log.info(f"Creating NEW ASSET: {asset_id} - {asset_name}")
                new_asset = Asset(
                    id=asset_id,
                    site_code="P01", # Default to P01
                    name=asset_name,
                    asset_type="MACHINE",
                    is_active=True,
                    created_at_utc=datetime.utcnow()
                )
                db.add(new_asset)
            else:
               log.debug(f"Asset {asset_id} already exists.")
        
        db.commit()
        log.info("Asset creation check complete.")

        # 2. Process Events
        req_count = 0
        for row in rows:
            asset_id = row.get("Asset ID")
            status_raw = row.get("\nOperational Status", "")
            if not status_raw:
                 # Fallback if key is clean
                 status_raw = row.get("Operational Status", "")
            status = status_raw.strip().upper() # OK / NOT OK
            log.info(f"Row Asset: {asset_id}, Status Raw: '{status_raw}', Status Parsed: '{status}'")
            reason = row.get("Issue / Work Description") or "Unknown Issue"
            ts_str = row.get("Timestamp")
            
            if not asset_id:
                continue
                
            occurred_at = parse_date(ts_str)
            
            # Create Timeline Event
            te_id = _new_id("EVT")
            
            # Determine logic
            # If NOT OK -> It's a stop or fault
            # If OK -> It's a resolution
            
            event_type = "STOP" if status == "NOT OK" else "STATUS_CHANGE"
            
            # Payload
            payload = {
                "original_status": status,
                "reason": reason,
                "csv_timestamp": ts_str,
                "imported": True
            }
            
            if status == "NOT OK":
                stop_id = _new_id("STOP")
                payload["stop_id"] = stop_id
                
                # Check if there is already an open stop for this asset?
                # For simplicity in this simulation, we just push a new open stop
                # OR we could check if one exists.
                # Let's just Add to StopQueue.
                
                sq = StopQueue(
                    id=stop_id,
                    site_code="P01",
                    asset_id=asset_id,
                    reason=reason,
                    is_open=True,
                    opened_at_utc=occurred_at,
                    closed_at_utc=None
                )
                db.add(sq)
                log.info(f"Active Stop logged for {asset_id}: {reason}")
            
            te = TimelineEvent(
                id=te_id,
                site_code="P01",
                event_type=event_type,
                asset_id=asset_id,
                occurred_at_utc=occurred_at,
                created_at_utc=datetime.utcnow(),
                correlation_id=f"csv:{te_id}",
                payload_json=payload
            )
            db.add(te)
            req_count += 1
            
        db.commit()
        log.info(f"Successfully processed {req_count} events from CSV.")
        
        # Verify
        stops = db.execute(select(StopQueue)).scalars().all()
        log.info(f"VERIFICATION: Total stops in DB now: {len(stops)}")
        for s in stops:
            log.info(f"Stop: {s.id}, Asset: {s.asset_id}")

    except Exception as e:
        log.error(f"Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    simulate()

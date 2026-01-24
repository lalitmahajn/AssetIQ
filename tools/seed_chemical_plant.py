"""
Chemical Plant Seed Script for AssetIQ
======================================
Generates a realistic chemical manufacturing environment (Polymer Plant).
Creates hierarchy, assets, master data, and 30 days of historical efficiency data.

Usage:
    python tools/seed_chemical_plant.py
"""

import os
import sys
import random
import uuid
import json
import hashlib
import hmac
import httpx
from datetime import datetime, timedelta

# Setup path to import apps code
sys.path.append(os.getcwd())

from common_core.db import PlantSessionLocal
from common_core.config import settings
from common_core.passwords import hash_pin
from apps.plant_backend import models, services

# --- CONSTANTS ---
SITE_CODE = settings.plant_site_code or "CHEM-01"
ACTOR_ID = "system_seed"


def get_db():
    return PlantSessionLocal()


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def sync_payload_to_hq(items: list):
    if not settings.hq_receiver_url:
        return
    payload = {"items": items}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = sign_payload(payload_bytes, settings.sync_hmac_secret)
    try:
        httpx.post(
            settings.hq_receiver_url,
            content=payload_bytes,
            headers={"X-Signature": sig, "Content-Type": "application/json"},
            timeout=5,
        )
    except Exception as e:
        print(f"HQ Sync warning: {e}")


# --- SEED FUNCTIONS ---


def seed_users(db):
    print(">> Seeding Users...")
    users = [
        {"id": "admin", "name": "Plant Manager", "role": "admin", "pin": "123456"},
        {"id": "operator", "name": "Line Operator", "role": "operator", "pin": "111111"},
        {"id": "maint", "name": "Maintenance Lead", "role": "maintenance", "pin": "222222"},
    ]
    for u in users:
        existing = db.get(models.User, u["id"])
        if not existing:
            usr = models.User(
                id=u["id"], full_name=u["name"], roles=u["role"], pin_hash=hash_pin(u["pin"])
            )
            db.add(usr)
    db.commit()


def seed_master_data(db):
    print(">> Seeding Master Data (Stop Reasons)...")
    # STOP REASONS
    reasons = [
        "High Pressure Trip",
        "Temperature Deviation",
        "Level Sensor Fault",
        "Seal Leakage",
        "Pump Vibration",
        "Safety Interlock Trip",
        "Catalyst Blockage",
        "Power Fluctuation",
        "Emergency Stop",
        "Routine Cleaning",
        "Valve Stuck",
    ]

    # Ensure Type Exists
    mt = db.query(models.MasterType).filter_by(type_code="STOP_REASON").first()
    if not mt:
        mt = models.MasterType(
            site_code=SITE_CODE,
            type_code="STOP_REASON",
            name="Stop Reason",
            created_at_utc=datetime.utcnow(),
        )
        db.add(mt)
        db.flush()

    # Create Items
    for name in reasons:
        code = name.upper().replace(" ", "_")
        exists = (
            db.query(models.MasterItem)
            .filter_by(master_type_code="STOP_REASON", item_code=code)
            .first()
        )
        if not exists:
            services.master_item_create(db, "STOP_REASON", code, name, actor_id=ACTOR_ID)
    db.commit()


def seed_assets(db):
    print(">> Seeding Assets (Hierarchy)...")
    existing_ct = db.query(models.Asset).count()
    if existing_ct > 0:
        print("   Assets already exist. Skipping creation.")
        return [a.id for a in db.query(models.Asset).filter(models.Asset.category != "AREA").all()]

    # 1. Level 1: Areas (Use 'AREA' category as per UI)
    areas = [
        {"id": "HALL-A", "name": "Polymer Production Hall", "cat": "AREA"},
        {"id": "UTILITY-B", "name": "Utility Building", "cat": "AREA"},
        {"id": "STORAGE-C", "name": "Bulk Storage Farm", "cat": "AREA"},
    ]
    for a in areas:
        services.asset_create(
            db,
            {
                "id": a["id"],
                "asset_code": a["id"],
                "name": a["name"],
                "category": a["cat"],
                "criticality": "high",
            },
            actor_user_id=ACTOR_ID,
            request_id="seed",
        )

    # 2. Level 2: Lines (Use 'AREA' category implies Area/Line)
    lines = [
        {
            "id": "LINE-1",
            "name": "Polymer Line 1 (High Viscosity)",
            "parent": "HALL-A",
            "cat": "AREA",
        },
        {
            "id": "LINE-2",
            "name": "Polymer Line 2 (Low Viscosity)",
            "parent": "HALL-A",
            "cat": "AREA",
        },
        {"id": "WATER-SYS", "name": "Cooling Water System", "parent": "UTILITY-B", "cat": "AREA"},
        {"id": "STEAM-SYS", "name": "Steam Generation", "parent": "UTILITY-B", "cat": "AREA"},
    ]
    for l in lines:
        services.asset_create(
            db,
            {
                "id": l["id"],
                "asset_code": l["id"],
                "name": l["name"],
                "category": l["cat"],
                "parent_id": l["parent"],
            },
            actor_user_id=ACTOR_ID,
            request_id="seed",
        )

    # 3. Level 3: Machines (Use 'MACHINE' category as per UI)
    machines = [
        # Line 1 (Critical Production)
        {
            "id": "R-101",
            "name": "Reactor 101",
            "parent": "LINE-1",
            "cat": "MACHINE",
            "crit": "high",
        },
        {
            "id": "EX-101",
            "name": "Extruder 101",
            "parent": "LINE-1",
            "cat": "MACHINE",
            "crit": "medium",
        },
        {
            "id": "CF-101",
            "name": "Centrifuge 101",
            "parent": "LINE-1",
            "cat": "MACHINE",
            "crit": "medium",
        },
        # Line 2 (Production)
        {
            "id": "R-201",
            "name": "Reactor 201",
            "parent": "LINE-2",
            "cat": "MACHINE",
            "crit": "high",
        },
        {
            "id": "D-201",
            "name": "Fluid Bed Dryer",
            "parent": "LINE-2",
            "cat": "MACHINE",
            "crit": "low",
        },
        # Utilities (Critical Infrastructure)
        {
            "id": "P-501",
            "name": "Main Cooling Pump A",
            "parent": "WATER-SYS",
            "cat": "MACHINE",
            "crit": "high",
        },
        {
            "id": "P-502",
            "name": "Backup Cooling Pump B",
            "parent": "WATER-SYS",
            "cat": "MACHINE",
            "crit": "high",
        },
        {
            "id": "B-601",
            "name": "Steam Boiler A",
            "parent": "STEAM-SYS",
            "cat": "MACHINE",
            "crit": "high",
        },
        {
            "id": "COMP-701",
            "name": "Plant Air Compressor",
            "parent": "UTILITY-B",
            "cat": "MACHINE",
            "crit": "medium",
        },
        # Storage
        {
            "id": "T-301",
            "name": "Monomer Feed Tank",
            "parent": "STORAGE-C",
            "cat": "MACHINE",
            "crit": "medium",
        },
        {
            "id": "T-302",
            "name": "Solvent Recovery Tank",
            "parent": "STORAGE-C",
            "cat": "MACHINE",
            "crit": "low",
        },
    ]

    machine_ids = []
    for m in machines:
        # Note: We append description about the machine type since Category is generic "MACHINE"
        services.asset_create(
            db,
            {
                "id": m["id"],
                "asset_code": m["id"],
                "name": m["name"],
                "category": m["cat"],
                "parent_id": m["parent"],
                "criticality": m["crit"],
                "is_critical": (m["crit"] == "high"),
                "description": f"Type: {m['name'].split()[0]}",
            },
            actor_user_id=ACTOR_ID,
            request_id="seed",
        )
        machine_ids.append(m["id"])

    db.commit()
    return machine_ids


def generate_history(db, asset_ids):
    print(">> Generating 30 Days of History...")
    reasons = [
        i.item_name
        for i in db.query(models.MasterItem).filter_by(master_type_code="STOP_REASON").all()
    ]

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    current = start_date

    while current < end_date:
        day_str = current.strftime("%Y-%m-%d")

        # Decide if this day has issues (random)
        daily_stops = []
        for aid in asset_ids:
            # EFFICIENCY PROFILES:
            # R-101: CRITICAL (Red) - Fails often, long duration
            # EX-101: WARNING (Yellow) - Fails moderately
            # Others: HEALTHY (Green) - Rare failures

            chance = 0.1  # Default Green
            min_dur, max_dur = 10, 60

            if aid == "R-101":
                chance = 0.85  # Fail almost every day
                min_dur, max_dur = 120, 300  # 2-5 hours downtime
            elif aid == "EX-101":
                chance = 0.40  # Fail often
                min_dur, max_dur = 60, 150  # 1-2.5 hours downtime

            if random.random() < chance:
                # Create a stop
                reason = random.choice(reasons)
                duration = random.randint(min_dur, max_dur)  # mins

                # Time
                hour = random.randint(0, 23)
                start_time = current.replace(hour=hour, minute=random.randint(0, 50))
                end_time = start_time + timedelta(minutes=duration)

                # 1. Open Stop
                res = services.open_stop(db, aid, reason, ACTOR_ID, None, None)
                db.flush()
                stop_id, ticket_id = res["stop_id"], res["ticket_id"]

                # 2. Close it (Historical)
                sq = db.get(models.StopQueue, stop_id)
                if sq:
                    sq.opened_at_utc = start_time
                    sq.closed_at_utc = end_time
                    sq.is_open = False
                    sq.resolution_text = "Auto-resolved by seed script"

                # 3. Close Ticket
                t = db.get(models.Ticket, ticket_id)
                if t:
                    t.created_at_utc = start_time
                    t.status = "CLOSED"
                    t.resolved_at_utc = end_time
                    t.close_note = "Fixed"

                # 4. Backdate Audit/Timeline (Crucial for Dashboard charts)
                # (Simplified: just update the DB records we have)

        db.commit()
        # Optional: Generate Rollup for HQ if needed (skipped for speed)

        current += timedelta(days=1)
        if current.day % 5 == 0:
            print(f"   Processed up to {day_str}")


def create_live_data(db, asset_ids):
    print(">> Creating LIVE Active Stops...")
    reasons = [
        i.item_name
        for i in db.query(models.MasterItem).filter_by(master_type_code="STOP_REASON").all()
    ]

    # Create 2 Open Stops
    targets = ["R-101", "P-501"]  # Critical Reactor and Pump
    for aid in targets:
        if aid in asset_ids:
            reason = f"Active Alarm: {random.choice(reasons)}"
            services.open_stop(db, aid, reason, ACTOR_ID, None, None)
            print(f"   OPEN STOP created on {aid}")
    db.commit()


def run_seed():
    db = get_db()
    try:
        seed_users(db)
        seed_master_data(db)
        machine_ids = seed_assets(db)
        generate_history(db, machine_ids)
        create_live_data(db, machine_ids)
        print("\n✅ Chemical Plant Simulation Complete!")
        print("   Login: admin / 123456")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()

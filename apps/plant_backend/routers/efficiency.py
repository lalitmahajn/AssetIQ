from __future__ import annotations

from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import select
from common_core.db import PlantSessionLocal
from common_core.config import settings
from apps.plant_backend.models import StopQueue, Asset
from apps.plant_backend.deps import require_perm

router = APIRouter(prefix="/ui/efficiency", tags=["efficiency"])


@router.get("/by-asset")
def get_efficiency_by_asset(days: int = 7, user=Depends(require_perm("stops.view"))):
    """
    Calculates efficiency per asset based on StopQueue data.
    Efficiency = (Total Window - Downtime) / Total Window * 100
    """
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        start_dt = now - timedelta(days=days)
        total_minutes = days * 24 * 60  # Total possible uptime in minutes

        # Get all stops in the window
        stops = db.execute(
            select(StopQueue).where(StopQueue.opened_at_utc >= start_dt)
        ).scalars().all()

        # Get all assets for reference
        assets = db.execute(select(Asset).where(Asset.is_active == True)).scalars().all()
        asset_map = {a.id: a.asset_code or a.id for a in assets}

        # Aggregate downtime by asset
        downtime_by_asset = {}
        for s in stops:
            asset_id = s.asset_id
            if s.closed_at_utc:
                dt_sec = (s.closed_at_utc - s.opened_at_utc).total_seconds()
            else:
                dt_sec = (now - s.opened_at_utc).total_seconds()
            downtime_by_asset[asset_id] = downtime_by_asset.get(asset_id, 0) + dt_sec

        # Build result for all assets (even those with 0 downtime)
        results = []
        for asset in assets:
            dt_min = int(downtime_by_asset.get(asset.id, 0) / 60)
            uptime_min = max(0, total_minutes - dt_min)
            efficiency = round((uptime_min / total_minutes) * 100, 1) if total_minutes > 0 else 100.0
            results.append({
                "asset_id": asset.id,
                "asset_code": asset_map.get(asset.id, asset.id),
                "efficiency_pct": efficiency,
                "downtime_minutes": dt_min,
                "uptime_minutes": uptime_min,
            })

        # Sort by efficiency ascending (worst first)
        results.sort(key=lambda x: x["efficiency_pct"])

        return {
            "window_days": days,
            "total_minutes": total_minutes,
            "items": results,
        }

    finally:
        db.close()

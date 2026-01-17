from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select

from apps.plant_backend.deps import require_perm
from apps.plant_backend.models import Asset, StopQueue
from common_core.db import PlantSessionLocal

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
        stops = (
            db.execute(select(StopQueue).where(StopQueue.opened_at_utc >= start_dt)).scalars().all()
        )

        # Get all assets for reference
        assets = db.execute(select(Asset).where(Asset.is_active)).scalars().all()

        asset_map = {a.id: a for a in assets}

        # Build hierarchy
        children_map = {}
        roots = []
        for a in assets:
            if a.parent_id:
                children_map.setdefault(a.parent_id, []).append(a.id)
            else:
                roots.append(a.id)

        # 1. Calculate Base Stats (Leaf Logic)
        base_stats = {}  # asset_id -> {downtime_sec, total_min}

        # Aggregate downtime by asset
        downtime_by_asset = {}
        for s in stops:
            asset_id = s.asset_id
            if s.closed_at_utc:
                dt_sec = (s.closed_at_utc - s.opened_at_utc).total_seconds()
            else:
                dt_sec = (now - s.opened_at_utc).total_seconds()

            downtime_by_asset[asset_id] = downtime_by_asset.get(asset_id, 0) + dt_sec

        for asset in assets:
            dt_min = int(downtime_by_asset.get(asset.id, 0) / 60)
            uptime_min = max(0, total_minutes - dt_min)
            eff = round((uptime_min / total_minutes) * 100, 1) if total_minutes > 0 else 100.0
            base_stats[asset.id] = {
                "downtime_minutes": dt_min,
                "uptime_minutes": uptime_min,
                "efficiency_pct": eff,
                "has_direct_stops": asset.id in downtime_by_asset,
            }

        # 2. Recursive Aggregation & Linearization

        def process_node(asset_id, level):
            children = children_map.get(asset_id, [])

            # Recurse first to get children stats
            child_stats_list = []
            for child_id in children:
                child_stats_list.append(process_node(child_id, level + 1))

            # Use base stats initially
            my_stats = base_stats[asset_id]
            final_stats = my_stats.copy()

            # If I have children, my efficiency is Average of Children (unless logic dictates otherwise)
            # Strategy: If node has no stops itself but has children, treat it as pure aggregator.
            # If node has stops AND children (rare for structure), we might need weighted avg.
            # Simple plan: If children exist, overwrite efficiency with avg(children_efficiency)
            # and sum(downtime).

            if children:
                # Sum downtime
                agg_downtime = sum(c["downtime_minutes"] for c in child_stats_list)
                # If the parent itself had stops, add them too (mixed node)
                agg_downtime += my_stats["downtime_minutes"]

                final_stats["downtime_minutes"] = agg_downtime
                final_stats["uptime_minutes"] = max(0, total_minutes - agg_downtime)

                # Average Efficiency
                if child_stats_list:
                    avg_eff = sum(c["efficiency_pct"] for c in child_stats_list) / len(
                        child_stats_list
                    )
                    final_stats["efficiency_pct"] = round(avg_eff, 1)

            # Add to result list (DFS Order)
            asset_obj = asset_map[asset_id]
            item = {
                "asset_id": asset_id,
                "asset_code": asset_obj.asset_code or asset_id,
                "asset_name": asset_obj.name,
                "efficiency_pct": final_stats["efficiency_pct"],
                "downtime_minutes": final_stats["downtime_minutes"],
                "uptime_minutes": final_stats["uptime_minutes"],
                "level": level,
                "is_parent": bool(children),
            }
            # We append to results list here? No, recursive function usually constructs/returns.
            # But we want a flat list.
            # Actually, because we need to return stats for the parent computation,
            # we should separate the list building.
            # Let's rebuild:
            return final_stats

        # Re-traverse to build list.
        # Actually proper way: do calc in one pass (post-order) then build list (pre-order)?
        # Or mixed. Helper that returns stats AND appends to list?
        # If we append to global `results` in the loop, we get Post-Order (children before parent).
        # We want Pre-Order for UI (Parent then children).
        # So we need to calculate stats first (Post-Order), then clean list (Pre-Order).

        # Step 2a: Calculate Stats Map (Post-Order)
        computed_stats = {}  # asset_id -> stats

        def calc_stats_recursive(asset_id):
            stats = base_stats[asset_id].copy()
            children = children_map.get(asset_id, [])

            if children:
                child_sum_eff = 0
                child_sum_dt = 0
                count_metrics = 0

                for cid in children:
                    c_stats = calc_stats_recursive(cid)
                    child_sum_eff += c_stats["efficiency_pct"]
                    child_sum_dt += c_stats["downtime_minutes"]
                    count_metrics += 1

                # Parent Logic: Avg Efficiency, Sum Downtime
                stats["downtime_minutes"] += child_sum_dt
                stats["uptime_minutes"] = max(0, total_minutes - stats["downtime_minutes"])
                stats["efficiency_pct"] = round(child_sum_eff / count_metrics, 1)

            computed_stats[asset_id] = stats
            return stats

        for r in roots:
            calc_stats_recursive(r)

        # Step 2b: Build List (Pre-Order)
        final_list = []

        def build_list_recursive(asset_id, level):
            stats = computed_stats[asset_id]
            asset_obj = asset_map[asset_id]

            final_list.append(
                {
                    "asset_id": asset_id,
                    "asset_code": asset_obj.asset_code or asset_id,
                    "asset_name": asset_obj.name,
                    "parent_id": asset_obj.parent_id,
                    "efficiency_pct": stats["efficiency_pct"],
                    "downtime_minutes": stats["downtime_minutes"],
                    "uptime_minutes": stats["uptime_minutes"],
                    "level": level,
                    "is_parent": bool(children_map.get(asset_id)),
                }
            )

            for cid in children_map.get(asset_id, []):
                build_list_recursive(cid, level + 1)

        for r in roots:
            build_list_recursive(r, 0)

        return {
            "window_days": days,
            "total_minutes": total_minutes,
            "items": final_list,
        }

    finally:
        db.close()

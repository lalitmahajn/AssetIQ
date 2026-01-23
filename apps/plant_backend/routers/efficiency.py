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

        # 1. Pre-process Stops into Intervals per Asset
        # asset_id -> list of (start_utc, end_utc) tuples
        asset_intervals: dict[str, list[tuple[datetime, datetime]]] = {}

        for s in stops:
            # Clip stop to window
            s_start = max(s.opened_at_utc, start_dt)
            s_end = s.closed_at_utc if s.closed_at_utc else now
            # Ensure start < end (sanity check)
            s_end = min(s_end, now)

            if s_start < s_end:
                asset_intervals.setdefault(s.asset_id, []).append((s_start, s_end))

        # Helper to merge intervals and calculate total minutes
        def get_merged_downtime_minutes(
            intervals: list[tuple[datetime, datetime]],
        ) -> tuple[int, list[tuple[datetime, datetime]]]:
            if not intervals:
                return 0, []

            # Sort by start time
            sorted_intervals = sorted(intervals, key=lambda x: x[0])
            merged = []

            if sorted_intervals:
                curr_start, curr_end = sorted_intervals[0]
                for next_start, next_end in sorted_intervals[1:]:
                    if next_start < curr_end:  # Overlap or adjacent
                        curr_end = max(curr_end, next_end)
                    else:
                        merged.append((curr_start, curr_end))
                        curr_start, curr_end = next_start, next_end
                merged.append((curr_start, curr_end))

            total_sec = sum((end - start).total_seconds() for start, end in merged)
            return int(total_sec / 60), merged

        # 2. Recursive Calculation (Post-Order Logic)
        computed_stats = {}  # asset_id -> stats dict

        def calc_recursive(asset_id):
            # Start with own intervals
            my_intervals = asset_intervals.get(asset_id, [])[:]

            children = children_map.get(asset_id, [])

            # Recurse for children
            for child_id in children:
                child_intervals, _ = calc_recursive(child_id)

                # CRITICALITY LOGIC:
                # If child is critical, its downtime intervals contribute to parent
                child_obj = asset_map[child_id]
                if child_obj.is_critical:
                    my_intervals.extend(child_intervals)

            # Merge overlaps & calculate stats
            dt_min, final_intervals = get_merged_downtime_minutes(my_intervals)
            upt_min = max(0, total_minutes - dt_min)
            eff = round((upt_min / total_minutes) * 100, 1) if total_minutes > 0 else 100.0

            # MTTR/MTTF/MTBF Calculation
            # "Failures" = number of distinct downtime events (merged intervals)
            stop_count = len(final_intervals)

            if stop_count > 0:
                mttr_min = dt_min / stop_count
                mttf_min = upt_min / stop_count
                mtbf_min = total_minutes / stop_count
            else:
                mttr_min = 0.0
                mttf_min = float(
                    total_minutes
                )  # No failures = infinite really, but bounded by window
                mtbf_min = float(total_minutes)

            stats = {
                "efficiency_pct": eff,
                "downtime_minutes": dt_min,
                "uptime_minutes": upt_min,
                "mttr_minutes": mttr_min,
                "mttf_minutes": mttf_min,
                "mtbf_minutes": mtbf_min,
                "stop_count": stop_count,
            }
            computed_stats[asset_id] = stats

            # Return final intervals to bubble up
            return final_intervals, stats

        for r in roots:
            calc_recursive(r)

        # 3. Build List (Pre-Order)
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
                    "mttr_minutes": stats["mttr_minutes"],
                    "mttf_minutes": stats["mttf_minutes"],
                    "mtbf_minutes": stats["mtbf_minutes"],
                    "stop_count": stats["stop_count"],
                    "level": level,
                    "is_parent": bool(children_map.get(asset_id)),
                    "is_critical": asset_obj.is_critical,
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

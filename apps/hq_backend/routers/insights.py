from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc, and_

from common_core.db import HQSessionLocal
from common_core.security_deps import require_perm
from apps.hq_backend.models import InsightDaily

router = APIRouter(prefix="/hq/insights", tags=["hq-insights"])


def _today_utc() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


@router.get("/overview")
def overview(day_utc: Optional[str] = None, _user=require_perm("insight.view")) -> Dict[str, Any]:
    day = day_utc or _today_utc()
    db = HQSessionLocal()
    try:
        rows = (
            db.execute(
                select(InsightDaily)
                .where(InsightDaily.day_utc == day)
                .order_by(desc(InsightDaily.severity), InsightDaily.site_code, InsightDaily.id)
            )
            .scalars()
            .all()
        )
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append(
                {
                    "day_utc": r.day_utc,
                    "site_code": r.site_code,
                    "insight_type": r.insight_type,
                    "title": r.title,
                    "severity": r.severity,
                    "detail": r.detail_json,
                    "created_at_utc": r.created_at_utc.isoformat(),
                }
            )

        return {"day_utc": day, "items": items}
    finally:
        db.close()


@router.get("/plant/{site_code}")
def by_plant(site_code: str, day_utc: Optional[str] = None, _user=require_perm("insight.view")) -> Dict[str, Any]:
    day = day_utc or _today_utc()
    db = HQSessionLocal()
    try:
        rows = (
            db.execute(
                select(InsightDaily)
                .where(and_(InsightDaily.day_utc == day, InsightDaily.site_code == site_code))
                .order_by(desc(InsightDaily.severity), InsightDaily.id)
            )
            .scalars()
            .all()
        )
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append(
                {
                    "day_utc": r.day_utc,
                    "site_code": r.site_code,
                    "insight_type": r.insight_type,
                    "title": r.title,
                    "severity": r.severity,
                    "detail": r.detail_json,
                    "created_at_utc": r.created_at_utc.isoformat(),
                }
            )

        return {"day_utc": day, "site_code": site_code, "items": items}
    finally:
        db.close()

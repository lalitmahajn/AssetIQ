from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc

from common_core.db import HQSessionLocal
from apps.hq_backend.models import ReportJob

router = APIRouter(prefix="/hq/reports", tags=["hq-reports"])


@router.get("/list")
def list_reports(limit: int = 50) -> Dict[str, Any]:
    limit = max(1, min(int(limit), 200))
    db = HQSessionLocal()
    try:
        rows = db.execute(select(ReportJob).order_by(desc(ReportJob.created_at_utc)).limit(limit)).scalars().all()
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append(
                {
                    "report_type": r.report_type,
                    "period_start_utc": r.period_start_utc,
                    "period_end_utc": r.period_end_utc,
                    "file_pdf": r.file_pdf,
                    "file_xlsx": r.file_xlsx,
                    "created_at_utc": r.created_at_utc.isoformat(),
                    "updated_at_utc": r.updated_at_utc.isoformat(),
                }
            )
        return {"items": items}
    finally:
        db.close()

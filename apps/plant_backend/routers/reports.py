from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from apps.plant_backend import services
from apps.plant_backend.deps import require_perm
from apps.plant_backend.models import ReportRequest
from common_core.config import settings
from common_core.db import PlantSessionLocal
from common_core.report_tokens import sign_download_token, verify_download_token

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequestIn(BaseModel):
    report_type: str
    date_from: str
    date_to: str
    filters: dict | None = {}


@router.post("/request")
def request_manual_report(body: ReportRequestIn, user=Depends(require_perm("report.manage"))):
    db = PlantSessionLocal()
    try:
        rr = services.report_request_create_and_generate_csv(
            db,
            report_type=body.report_type,
            date_from=body.date_from,
            date_to=body.date_to,
            filters=body.filters or {},
            actor_user_id=user["sub"],
            actor_station_code=None,
            request_id=None,
        )
        db.commit()
        return {"ok": True, "id": rr.id, "status": rr.status}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/list-requests")
def list_report_requests(user=Depends(require_perm("report.view"))):
    db = PlantSessionLocal()
    try:
        rows = (
            db.execute(
                select(ReportRequest)
                .where(ReportRequest.site_code == settings.plant_site_code)
                .order_by(ReportRequest.id.desc())
                .limit(50)
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": r.id,
                "report_type": r.report_type,
                "date_from": r.date_from.isoformat(),
                "date_to": r.date_to.isoformat(),
                "status": r.status,
                "generated_file_path": r.generated_file_path,
                "error_message": r.error_message,
                "created_at_utc": r.created_at_utc.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()


# Existing Vault Logic
@router.post("/issue-download")
def issue(body: dict, user=Depends(require_perm("report.view"))):
    rel_path = body.get("rel_path", "")
    if not rel_path:
        # Fallback to checking if it's a request ID
        req_id = body.get("report_request_id")
        if req_id:
            db = PlantSessionLocal()
            rr = db.get(ReportRequest, req_id)
            db.close()
            if rr and rr.generated_file_path:
                rel_path = rr.generated_file_path

    if not rel_path:
        raise HTTPException(status_code=400, detail="rel_path or report_request_id required")

    safe = rel_path.replace("\\", "/").lstrip("/")
    # Check if it's in hot/ archive/ cold/ OR a report file from manual request
    is_valid_root = (
        safe.startswith("hot/")
        or safe.startswith("archive/")
        or safe.startswith("cold/")
        or safe.endswith(".csv")
        or safe.endswith(".pdf")
        or safe.endswith(".xlsx")
    )
    if not is_valid_root:
        raise HTTPException(status_code=400, detail="invalid_path")

    token = sign_download_token(site_code=settings.plant_site_code, rel_path=safe, ttl_seconds=3600)
    return {"token": token}


@router.get("/download")
def download(token: str):
    try:
        payload = verify_download_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    rel = payload["rel_path"].replace("\\", "/").lstrip("/")
    full = os.path.normpath(os.path.join(settings.report_vault_root, rel))
    if not full.startswith(os.path.normpath(settings.report_vault_root)):
        raise HTTPException(status_code=400, detail="bad path")
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(full, filename=os.path.basename(full))


@router.get("/list-vault")
def list_vault_files(user=Depends(require_perm("report.view"))):
    root = settings.report_vault_root
    results = []
    if os.path.exists(root):
        for dirpath, dirnames, filenames in os.walk(root):
            for f in filenames:
                if f.lower().endswith((".pdf", ".xlsx", ".csv")):
                    full_path = os.path.join(dirpath, f)
                    rel_path = os.path.relpath(full_path, root).replace("\\", "/")
                    stat = os.stat(full_path)
                    results.append(
                        {
                            "name": f,
                            "rel_path": rel_path,
                            "size": stat.st_size,
                            "mtime": int(stat.st_mtime),
                            "type": "PDF"
                            if f.lower().endswith(".pdf")
                            else ("EXCEL" if f.lower().endswith(".xlsx") else "CSV"),
                        }
                    )
    results.sort(key=lambda x: x["mtime"], reverse=True)
    return {"items": results[:100]}

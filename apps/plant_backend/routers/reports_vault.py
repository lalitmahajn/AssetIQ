from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import os

from common_core.config import settings
from common_core.report_tokens import sign_download_token, verify_download_token
from apps.plant_backend.deps import require_perm

router = APIRouter(prefix="/reports", tags=["reports-vault"])

@router.post("/issue-download")
def issue(body: dict, user=Depends(require_perm("ticket.view"))):
    rel_path = body.get("rel_path","")
    if not rel_path:
        raise HTTPException(status_code=400, detail="rel_path required")
    safe = rel_path.replace("\\","/").lstrip("/")
    if not (safe.startswith("hot/") or safe.startswith("archive/") or safe.startswith("cold/")):
        raise HTTPException(status_code=400, detail="rel_path must start with hot/ archive/ or cold/")
    token = sign_download_token(site_code=settings.plant_site_code, rel_path=safe, ttl_seconds=3600)
    return {"token": token}

@router.get("/download")
def download(token: str):
    try:
        payload = verify_download_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    rel = payload["rel_path"].replace("\\","/").lstrip("/")
    full = os.path.normpath(os.path.join(settings.report_vault_root, rel))
    if not full.startswith(os.path.normpath(settings.report_vault_root)):
        raise HTTPException(status_code=400, detail="bad path")
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(full, filename=os.path.basename(full))

@router.get("/list")
def list_files(user=Depends(require_perm("ticket.view"))):
    # List files in report vault
    # Structure: hot/YYYY/MM/...
    # For simplicity, let's walk the directory and return PDF/XLSX files.
    root = settings.report_vault_root
    results = []
    if os.path.exists(root):
        for dirpath, dirnames, filenames in os.walk(root):
            for f in filenames:
                if f.lower().endswith(".pdf") or f.lower().endswith(".xlsx"):
                    full_path = os.path.join(dirpath, f)
                    rel_path = os.path.relpath(full_path, root).replace("\\", "/")
                    stat = os.stat(full_path)
                    results.append({
                        "name": f,
                        "rel_path": rel_path,
                        "size": stat.st_size,
                        "mtime": int(stat.st_mtime),
                        "type": "PDF" if f.lower().endswith(".pdf") else "EXCEL"
                    })
    # Sort by mtime desc
    results.sort(key=lambda x: x["mtime"], reverse=True)
    return {"items": results[:100]} # Limit 100 recent

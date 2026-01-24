from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from apps.plant_backend.deps import require_perm
from common_core.config import settings

router = APIRouter(prefix="/backups", tags=["backups"])


def get_backup_dir() -> Path:
    return Path(settings.report_vault_root) / "backups"


@router.get("/list")
def list_backups(user=Depends(require_perm("master.view"))):
    """Lists available backup files."""
    backup_dir = get_backup_dir()
    if not backup_dir.exists():
        return []

    files = []
    for p in backup_dir.glob("*.sql.gz"):
        stat = p.stat()
        files.append(
            {
                "filename": p.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at_ts": stat.st_mtime,
                "created_at_fmt": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%d %b %Y, %I:%M %p"
                ),
            }
        )

    # Sort by newest first
    files.sort(key=lambda x: x["created_at_ts"], reverse=True)
    return files


@router.get("/download/{filename}")
def download_backup(filename: str, user=Depends(require_perm("master.manage"))):
    """Downloads a specific backup file."""
    # Security: Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    backup_dir = get_backup_dir()
    file_path = backup_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=file_path, filename=filename, media_type="application/gzip")


@router.post("/trigger")
def trigger_backup(user=Depends(require_perm("master.manage"))):
    """
    Triggers an immediate backup (Async via Flag/File or Direct?).
    Since Backend and Worker are separate, Backend cannot call Worker functions directly easily
    unless we use a queue or shared signal.

    SIMPLEST approach for MVP:
    Backend runs the backup using the same logic logic imported from shared code?
    No, MaintenanceAgent is in `apps.plant_worker`.
    Backend doesn't have `postgresql-client` installed?
    Checking Dockerfile.plant_backend... It relies on pip install.

    If Backend cannot run pg_dump, we must signal Worker.
    Signal: Touch a file named `TRIGGER_BACKUP` in the vault.
    Worker checks this file? No, worker only wakes up every 2s for SLAs.

    BETTER approach:
    Backend *can* install postgresql-client too.
    Let's modify Dockerfile.plant_backend to include postgresql-client.
    Then we can import `run_backup_job` code?
    Warning: `maintenance_agent.py` imports `models.py` etc so it is shared code compatible.

    Let's assume we update backend dockerfile too.
    """
    # For now, let's try to run it. If it fails due to missing pg_dump, we know why.
    # We will copy the code logic or move logic to `services.py`?
    # `maintenance_agent.py` is in `apps.plant_worker`. Imports from `apps` are fine if in pythonpath.

    try:
        from apps.plant_worker.maintenance_agent import run_backup_job

        success = run_backup_job()
        if not success:
            raise HTTPException(status_code=500, detail="Backup job returned failure")
        return {"status": "ok", "message": "Backup completed successfully"}
    except ImportError:
        # Fallback if worker package is not importable (should be fine as they share volume mapping of code?)
        # Docker map: `../../:/app`. So `apps.plant_worker` exists.
        # But `postgresql-client` might be missing on backend container.
        raise HTTPException(
            status_code=500, detail="Configuration Error: Backend cannot execute backup logic."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Import needed for file listing
from datetime import datetime

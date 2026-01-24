from __future__ import annotations

import glob
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select, text

from apps.plant_backend.models import (
    AuditLog,
    EmailQueue,
    EventOutbox,
    StopQueue,
    Ticket,
    TimelineEvent,
    WhatsAppQueue,
)
from common_core.config import settings
from common_core.db import PlantSessionLocal

log = logging.getLogger("assetiq.maintenance")


def get_backup_dir() -> Path:
    root = Path(settings.report_vault_root)
    backup_dir = root / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def run_backup_job() -> bool:
    """Runs a full database backup using pg_dump."""
    log.info("Starting database backup...")
    try:
        backup_dir = get_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"db_backup_{settings.plant_site_code}_{timestamp}.sql.gz"
        filepath = backup_dir / filename

        # Parse DB URL to get connection details for pg_dump
        # URL format: postgresql+psycopg2://user:pass@host:port/dbname
        # We can rely on libpq env vars if we set them, or just use the PGPASSWORD env var
        # simpler to just construct the command since we are inside the container network

        # Extract from settings.plant_db_url or env
        # Let's use the explicit env vars passed to the container if available,
        # but the app typically uses connection string.
        # Robust way: Parse the connection string.
        from sqlalchemy.engine.url import make_url

        u = make_url(settings.plant_db_url)

        env = os.environ.copy()
        env["PGPASSWORD"] = u.password

        cmd = [
            "pg_dump",
            "-h",
            u.host,
            "-p",
            str(u.port),
            "-U",
            u.username,
            "-d",
            u.database,
            "--no-owner",  # Safer for restores
            "--no-acl",
            "--clean",  # Drop objects before creation
            "--if-exists",
        ]

        # We pipe output to gzip
        with open(filepath, "wb") as f:
            p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env)
            p2 = subprocess.Popen(["gzip"], stdin=p1.stdout, stdout=f)
            p1.stdout.close()  # Allow p1 to receive SIGPIPE if p2 exits
            output, _ = p2.communicate()

            if p2.returncode != 0:
                raise Exception(f"gzip failed with code {p2.returncode}")
            if p1.wait() != 0:
                raise Exception(f"pg_dump failed with code {p1.returncode}")

        size_mb = filepath.stat().st_size / (1024 * 1024)
        log.info(f"Backup complete: {filename} ({size_mb:.2f} MB)")

        # Retention Policy for Backups
        retention = settings.backup_retention_days
        if retention > 0:
            prune_backups(backup_dir, retention)

        return True
    except Exception as e:
        log.error(f"Backup failed: {e}")
        return False


def prune_backups(backup_dir: Path, days: int):
    cutoff = datetime.now() - timedelta(days=days)
    log.info(f"Pruning backups older than {days} days...")
    count = 0
    for p in backup_dir.glob("*.sql.gz"):
        if datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
            p.unlink()
            count += 1
    log.info(f"Pruned {count} old backups.")


def run_cleanup_job() -> dict:
    """Prunes old data from the database."""
    log.info("Starting database cleanup...")
    summary = {}
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()

        # 1. Logs & Timeline (Log Retention)
        log_cut = now - timedelta(days=settings.log_retention_days)

        # Optimize: Use raw SQL for bulk deletes if ORM is too slow, but ORM is safer for starters
        # Audit Logs
        res = db.execute(delete(AuditLog).where(AuditLog.created_at_utc < log_cut))
        summary["audit_logs"] = res.rowcount

        # Timeline Events
        res = db.execute(delete(TimelineEvent).where(TimelineEvent.created_at_utc < log_cut))
        summary["timeline"] = res.rowcount

        # 2. Queues (Queue Retention)
        queue_cut = now - timedelta(days=settings.queue_retention_days)

        res = db.execute(delete(WhatsAppQueue).where(WhatsAppQueue.created_at_utc < queue_cut))
        summary["whatsapp_queue"] = res.rowcount

        res = db.execute(delete(EmailQueue).where(EmailQueue.created_at_utc < queue_cut))
        summary["email_queue"] = res.rowcount

        # Event Outbox (Only delete processed ones? No, usually safe to delete all old ones)
        # But safest is to delete ONLY sent ones.
        res = db.execute(
            delete(EventOutbox).where(
                EventOutbox.created_at_utc < queue_cut, EventOutbox.sent_at_utc.is_not(None)
            )
        )
        summary["event_outbox"] = res.rowcount

        # 3. Operations (Ticket Retention)
        # Only delete CLOSED tickets and CLOSED stops
        if settings.ticket_retention_days > 0:
            ticket_cut = now - timedelta(days=settings.ticket_retention_days)

            # Stops first (FK dependency? usually Ticket -> Stop)
            # Actually Ticket has stop_id.
            # We should query IDs to delete to ensure consistency or rely on CASCADE?
            # Let's delete Tickets first, then orphaned Stops? Or simpler:

            # Delete Closed Tickets
            res = db.execute(
                delete(Ticket).where(Ticket.status == "CLOSED", Ticket.resolved_at_utc < ticket_cut)
            )
            summary["tickets"] = res.rowcount

            # Delete Closed Stops
            res = db.execute(
                delete(StopQueue).where(
                    StopQueue.is_open.is_(False), StopQueue.closed_at_utc < ticket_cut
                )
            )
            summary["stops"] = res.rowcount

        db.commit()
        log.info(f"Cleanup complete: {summary}")
        return summary
    except Exception as e:
        log.error(f"Cleanup failed: {e}")
        db.rollback()
        return {}
    finally:
        db.close()


def check_startup_backup():
    """Checks if we missed a daily backup and runs it if needed."""
    backup_dir = get_backup_dir()
    files = list(backup_dir.glob("*.sql.gz"))

    should_run = False
    if not files:
        log.info("No backups found. Triggering initial backup.")
        should_run = True
    else:
        # Check latest file
        latest = max(files, key=os.path.getmtime)
        age_hours = (
            datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
        ).total_seconds() / 3600
        if age_hours > 26:
            log.info(f"Latest backup is {age_hours:.1f} hours old. Triggering catch-up backup.")
            should_run = True
        else:
            log.info(f"Backup status healthy (Latest: {age_hours:.1f}h ago).")

    if should_run:
        run_backup_job()

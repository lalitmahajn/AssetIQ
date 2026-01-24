from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, date

from apps.plant_worker.critical_alerts import send_critical_alert
from apps.plant_worker.email_sender import send_pending
from apps.plant_worker.maintenance_agent import (
    check_startup_backup,
    run_backup_job as run_maintenance_backup,
    run_cleanup_job as run_maintenance_cleanup,
)
from apps.plant_worker.report_archiver import run_once as archive_once
from apps.plant_worker.report_scheduler import run_once as check_reports_once
from apps.plant_worker.rollup_agent import compute_rollup_once
from apps.plant_worker.sync_agent import push_once
from common_core.guardrails import validate_runtime_secrets
from common_core.logging_setup import configure_logging

log = logging.getLogger("assetiq.worker")


def main() -> None:
    configure_logging(component="plant_worker")
    validate_runtime_secrets()
    log.info("worker_started", extra={"component": "plant_worker"})

    # Startup Recovery
    try:
        check_startup_backup()
    except Exception as e:
        log.error("startup_backup_check_failed", extra={"err": str(e)})

    last_archive = 0.0

    email_fail_streak = 0
    sync_fail_streak = 0

    last_rollup = 0.0
    last_report_check = 0.0
    last_sla_check = 0.0

    # Track days to avoid running multiple times per hour
    # We initialize to yesterday so it runs today if the hour matches immediately
    # We initialize to yesterday so it runs today if the hour matches immediately

    last_backup_date = date.today() - timedelta(days=1)
    last_cleanup_date = date.today() - timedelta(days=1)

    # But if we just started, we rely on check_startup_backup for the immediate backup.
    # The scheduler handles the NEXT recurrence (tomorrow 2am).
    # Actually, if we start at 02:30 AM, 'last_backup_date' logic above would trigger it instantly?
    # No, condition is `hour == 2`. If started at 02:30, it runs. If 08:00, checks hour 8 != 2.
    # To prevent double run if startup check already ran:
    last_backup_date = date.today()  # Assume handled for today by startup check or skipped
    last_cleanup_date = date.today()

    while True:
        try:
            sent = send_pending(limit=50)
            email_fail_streak = 0
            if sent:
                log.info("email_sent_batch", extra={"component": "plant_worker", "count": sent})
        except Exception as e:
            email_fail_streak += 1
            log.error("email_send_failed", extra={"err": str(e), "streak": email_fail_streak})
            if email_fail_streak >= 3:
                send_critical_alert("plant_worker_email_fail", str(e))

        try:
            pushed = push_once(batch=100)
            sync_fail_streak = 0
            if pushed:
                log.info("sync_pushed_batch", extra={"component": "plant_worker", "count": pushed})
        except Exception as e:
            sync_fail_streak += 1
            log.error("sync_push_failed", extra={"err": str(e), "streak": sync_fail_streak})
            if sync_fail_streak >= 3:
                send_critical_alert("plant_worker_sync_fail", str(e))

        try:
            now = time.time()
            if now - last_rollup > 60 and compute_rollup_once():
                last_rollup = now
                log.info("rollup_computed", extra={"component": "plant_worker"})
        except Exception as e:
            log.error("rollup_failed", extra={"err": str(e)})

        now = time.time()
        # Check for automated reports every hour
        if now - last_report_check > 3600:
            try:
                check_reports_once()
                last_report_check = now
                log.info("automated_report_check_ok", extra={"component": "plant_worker"})
            except Exception as e:
                log.error("automated_report_check_failed", extra={"err": str(e)})

        now = time.time()
        if now - last_archive > 3600:
            try:
                archive_once()
                last_archive = now
                log.info("report_archive_ok", extra={"component": "plant_worker"})
            except Exception as e:
                log.error("report_archive_failed", extra={"err": str(e)})
                send_critical_alert("plant_worker_archive_fail", str(e))

        # -------------------------------
        # Maintenance Scheduler (Daily)
        # -------------------------------
        current_dt = datetime.now()

        # 1. Daily Backup (02:00 AM)
        if current_dt.hour == 2 and last_backup_date != current_dt.date():
            try:
                run_maintenance_backup()
                last_backup_date = current_dt.date()
            except Exception as e:
                log.error("scheduled_backup_failed", extra={"err": str(e)})

        # 2. Daily Cleanup (03:00 AM)
        if current_dt.hour == 3 and last_cleanup_date != current_dt.date():
            try:
                run_maintenance_cleanup()
                last_cleanup_date = current_dt.date()
            except Exception as e:
                log.error("scheduled_cleanup_failed", extra={"err": str(e)})

        # Check for SLA warnings every 20 seconds
        now = time.time()
        if now - last_sla_check > 20:
            try:
                from apps.plant_backend.services import check_sla_breaches, check_sla_warnings
                from common_core.db import PlantSessionLocal

                db = PlantSessionLocal()
                try:
                    warned = check_sla_warnings(db)
                    if warned:
                        log.info(
                            "sla_warnings_sent",
                            extra={"component": "plant_worker", "count": warned},
                        )

                    breached = check_sla_breaches(db)
                    if breached:
                        log.info(
                            "sla_breaches_sent",
                            extra={"component": "plant_worker", "count": breached},
                        )
                finally:
                    db.close()
                last_sla_check = now
            except Exception as e:
                log.error("sla_warning_check_failed", extra={"err": str(e)})

        time.sleep(2)


if __name__ == "__main__":
    main()

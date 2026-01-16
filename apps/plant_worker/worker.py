from __future__ import annotations

import logging
import time

from common_core.logging_setup import configure_logging
from common_core.guardrails import validate_runtime_secrets

from apps.plant_worker.email_sender import send_pending
from apps.plant_worker.report_archiver import run_once as archive_once
from apps.plant_worker.sync_agent import push_once
from apps.plant_worker.rollup_agent import compute_rollup_once
from apps.plant_worker.report_scheduler import run_once as check_reports_once

log = logging.getLogger("assetiq.worker")


def main() -> None:
    configure_logging(component="plant_worker")
    validate_runtime_secrets()
    log.info("worker_started", extra={"component": "plant_worker"})
    last_archive = 0.0

    email_fail_streak = 0
    sync_fail_streak = 0

    last_rollup = 0.0
    last_report_check = 0.0

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
            if now - last_rollup > 60:
                if compute_rollup_once():
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

        time.sleep(2)


if __name__ == "__main__":
    main()

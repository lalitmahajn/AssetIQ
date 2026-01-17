from __future__ import annotations

import contextlib
import logging
import smtplib
import time
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import and_, desc, func, select

from apps.hq_backend.intelligence import recompute_and_store_daily_insights
from apps.hq_backend.models import (
    EmailQueue,
    ReportJob,
    RollupDaily,
    StopReasonDaily,
    TimelineEventHQ,
)
from common_core.config import settings
from common_core.db import HQSessionLocal
from common_core.guardrails import validate_runtime_secrets
from common_core.logging_setup import configure_logging

log = logging.getLogger("assetiq.hq_worker")


def _now() -> datetime:
    return datetime.utcnow()


def _utc_day(d: date) -> str:
    return d.isoformat()


def _send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not to_email:
        log.error(
            "smtp_not_configured",
            extra={"component": "hq_worker", "to": to_email, "subject": subject},
        )
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
        s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_pass)
        s.send_message(msg)


def _process_email_queue() -> int:
    db = HQSessionLocal()
    sent = 0
    try:
        rows = (
            db.execute(
                select(EmailQueue)
                .where(EmailQueue.status == "PENDING")
                .order_by(EmailQueue.id)
                .limit(20)
            )
            .scalars()
            .all()
        )
        for e in rows:
            try:
                _send_email(e.to_email, e.subject, e.body)
                e.status = "SENT"
                e.sent_at_utc = _now()
                sent += 1
            except Exception:
                e.status = "FAILED"
                db.commit()
                log.exception("hq_email_send_failed", extra={"component": "hq_worker", "id": e.id})
        db.commit()
        return sent
    finally:
        db.close()


def _rebuild_stop_reason_daily(target_day_utc: str) -> int:
    # Aggregate from HQ timeline events
    db = HQSessionLocal()
    try:
        day_start = datetime.fromisoformat(target_day_utc)
        day_end = day_start + timedelta(days=1)

        rows = db.execute(
            select(
                TimelineEventHQ.site_code,
                TimelineEventHQ.reason_code,
                func.count(TimelineEventHQ.id).label("stops"),
                func.sum(TimelineEventHQ.duration_seconds).label("dur"),
            )
            .where(
                TimelineEventHQ.occurred_at_utc >= day_start,
                TimelineEventHQ.occurred_at_utc < day_end,
                TimelineEventHQ.event_type == "STOP_RESOLVE",
                TimelineEventHQ.reason_code.is_not(None),
            )
            .group_by(TimelineEventHQ.site_code, TimelineEventHQ.reason_code)
            .order_by(desc(func.sum(TimelineEventHQ.duration_seconds)))
        ).all()

        # Upsert each (site, reason)
        upserts = 0
        for site_code, reason_code, stops, dur in rows:
            if not reason_code:
                continue
            downtime_minutes = int((int(dur or 0) + 59) / 60)
            existing = db.execute(
                select(StopReasonDaily).where(
                    StopReasonDaily.site_code == site_code,
                    StopReasonDaily.day_utc == target_day_utc,
                    StopReasonDaily.reason_code == reason_code,
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    StopReasonDaily(
                        site_code=site_code,
                        day_utc=target_day_utc,
                        reason_code=reason_code,
                        stops=int(stops or 0),
                        downtime_minutes=downtime_minutes,
                    )
                )
            else:
                existing.stops = int(stops or 0)
                existing.downtime_minutes = downtime_minutes
            upserts += 1

        db.commit()
        return upserts
    finally:
        db.close()


def _ensure_report_dir() -> Path:
    root = Path(settings.report_vault_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "hq").mkdir(parents=True, exist_ok=True)
    return root / "hq"


def _report_paths(report_type: str, start: str, end: str) -> tuple[Path, Path]:
    base = _ensure_report_dir()
    stem = f"{report_type}_{start}_to_{end}"
    return (base / f"{stem}.pdf", base / f"{stem}.xlsx")


def _generate_report(report_type: str, start_day: str, end_day: str) -> tuple[str, str]:
    pdf_path, xlsx_path = _report_paths(report_type, start_day, end_day)

    db = HQSessionLocal()
    try:
        rollups = (
            db.execute(
                select(RollupDaily)
                .where(and_(RollupDaily.day_utc >= start_day, RollupDaily.day_utc <= end_day))
                .order_by(RollupDaily.day_utc, RollupDaily.site_code)
            )
            .scalars()
            .all()
        )

        # ---- PDF ----
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        w, h = A4
        y = h - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, f"AssetIQ HQ Report: {report_type}")
        y -= 18
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"Period (UTC): {start_day} to {end_day}")
        y -= 22

        # Phase-3 Intelligence summary (read-only) – included only if enabled and data exists
        if settings.enable_intelligence:
            try:
                from apps.hq_backend.models import (
                    InsightDaily,  # local import to avoid worker start issues
                )

                ins_rows = (
                    db.execute(
                        select(InsightDaily)
                        .where(InsightDaily.day_utc == end_day)
                        .order_by(desc(InsightDaily.severity), InsightDaily.id)
                        .limit(8)
                    )
                    .scalars()
                    .all()
                )
                if ins_rows:
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(40, y, "HQ Insights Summary (read-only)")
                    y -= 14
                    c.setFont("Helvetica", 9)
                    for ins in ins_rows:
                        label = (
                            f"[{ins.severity}] "
                            + (f"{ins.site_code}: " if ins.site_code else "")
                            + ins.title
                        )
                        c.drawString(40, y, label[:110])
                        y -= 12
                        if y < 90:
                            c.showPage()
                            y = h - 40
                            c.setFont("Helvetica", 9)
                    y -= 10
            except Exception:
                log.exception("hq_report_insights_failed", extra={"component": "hq_worker"})

        # Rollups table
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, "Day")
        c.drawString(120, y, "Plant")
        c.drawString(190, y, "Downtime(min)")
        c.drawString(280, y, "Stops")
        c.drawString(330, y, "SLA Breaches")
        y -= 14
        c.setFont("Helvetica", 9)

        for r in rollups:
            c.drawString(40, y, r.day_utc)
            c.drawString(120, y, r.site_code)
            c.drawString(190, y, str(r.downtime_minutes))
            c.drawString(280, y, str(r.stops))
            c.drawString(330, y, str(r.sla_breaches))
            y -= 12
            if y < 80:
                c.showPage()
                y = h - 40
                c.setFont("Helvetica", 9)

        c.save()

        # ---- XLSX ----
        wb = Workbook()
        ws = wb.active
        ws.title = "Rollups"
        ws.append(
            [
                "day_utc",
                "site_code",
                "downtime_minutes",
                "stops",
                "sla_breaches",
                "tickets_open",
                "faults",
            ]
        )
        for r in rollups:
            ws.append(
                [
                    r.day_utc,
                    r.site_code,
                    r.downtime_minutes,
                    r.stops,
                    r.sla_breaches,
                    r.tickets_open,
                    r.faults,
                ]
            )

        if settings.enable_intelligence:
            try:
                from apps.hq_backend.models import InsightDaily

                ws2 = wb.create_sheet("Insights")
                ws2.append(["day_utc", "site_code", "severity", "insight_type", "title"])
                ins_rows = (
                    db.execute(
                        select(InsightDaily)
                        .where(InsightDaily.day_utc == end_day)
                        .order_by(desc(InsightDaily.severity), InsightDaily.id)
                    )
                    .scalars()
                    .all()
                )
                for ins in ins_rows:
                    ws2.append(
                        [
                            ins.day_utc,
                            ins.site_code or "",
                            ins.severity,
                            ins.insight_type,
                            ins.title,
                        ]
                    )
            except Exception:
                log.exception("hq_report_insights_xlsx_failed", extra={"component": "hq_worker"})

        wb.save(str(xlsx_path))

        return str(pdf_path), str(xlsx_path)
    finally:
        db.close()


def _ensure_report_job(report_type: str, start_day: str, end_day: str) -> bool:
    db = HQSessionLocal()
    now = _now()
    try:
        existing = db.execute(
            select(ReportJob).where(
                ReportJob.report_type == report_type,
                ReportJob.period_start_utc == start_day,
                ReportJob.period_end_utc == end_day,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return False

        pdf_path, xlsx_path = _generate_report(report_type, start_day, end_day)
        db.add(
            ReportJob(
                report_type=report_type,
                period_start_utc=start_day,
                period_end_utc=end_day,
                file_pdf=pdf_path,
                file_xlsx=xlsx_path,
                created_at_utc=now,
                updated_at_utc=now,
            )
        )
        db.commit()
        log.info(
            "hq_report_generated",
            extra={
                "component": "hq_worker",
                "type": report_type,
                "start": start_day,
                "end": end_day,
            },
        )
        return True
    finally:
        db.close()


def _schedule_reports() -> int:
    # Generate "yesterday" daily, last 7 days weekly, previous month monthly (UTC)
    today = datetime.utcnow().date()
    yday = today - timedelta(days=1)
    made = 0

    # daily
    if _ensure_report_job("DAILY", _utc_day(yday), _utc_day(yday)):
        made += 1

    # weekly (rolling last 7 days ending yesterday)
    start = yday - timedelta(days=6)
    if _ensure_report_job("WEEKLY", _utc_day(start), _utc_day(yday)):
        made += 1

    # monthly (previous calendar month)
    first_this = today.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    first_prev = last_prev.replace(day=1)
    if _ensure_report_job("MONTHLY", _utc_day(first_prev), _utc_day(last_prev)):
        made += 1

    return made


def main() -> None:
    configure_logging(component="hq_worker")
    validate_runtime_secrets()
    log.info("worker_started", extra={"component": "hq_worker"})

    # Simple deterministic loop
    while True:
        try:
            # rebuild yesterday stop-reason aggregates (safe, idempotent)
            yday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
            n = _rebuild_stop_reason_daily(yday)
            if n:
                log.info(
                    "hq_stop_reason_aggregated",
                    extra={"component": "hq_worker", "day_utc": yday, "rows": n},
                )
                if settings.enable_intelligence:
                    made_ins = recompute_and_store_daily_insights(
                        yday, window_days=settings.intelligence_window_days
                    )
                    log.info(
                        "hq_insights_recomputed",
                        extra={"component": "hq_worker", "day_utc": yday, "count": made_ins},
                    )

                    if settings.enable_intelligence_digest and settings.intelligence_digest_to:
                        # weekly digest trigger: Mondays (UTC)
                        try:
                            if datetime.utcnow().weekday() == 0:
                                _send_email(
                                    settings.intelligence_digest_to,
                                    "AssetIQ HQ Insights Digest",
                                    f"HQ insights updated for {yday}. Open the HQ dashboard for details.",
                                )
                                log.info(
                                    "hq_insights_digest_sent",
                                    extra={"component": "hq_worker", "day_utc": yday},
                                )
                        except Exception:
                            log.exception(
                                "hq_insights_digest_failed", extra={"component": "hq_worker"}
                            )

            made = _schedule_reports()
            if made:
                log.info("hq_reports_scheduled", extra={"component": "hq_worker", "count": made})

            sent = _process_email_queue()
            if sent:
                log.info("hq_email_sent", extra={"component": "hq_worker", "count": sent})
        except Exception:
            log.exception("hq_worker_failed", extra={"component": "hq_worker"})
            # alert IT via smtp if configured
            with contextlib.suppress(Exception):
                _send_email(
                    settings.email_it, "AssetIQ HQ worker failure", "hq_worker_failed (check logs)"
                )

        time.sleep(30)


if __name__ == "__main__":
    main()

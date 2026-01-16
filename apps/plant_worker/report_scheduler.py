from datetime import datetime, timedelta
import logging
from sqlalchemy import select
from common_core.db import PlantSessionLocal
from common_core.config import settings
from apps.plant_backend.models import ReportRequest
from apps.plant_backend import services

log = logging.getLogger("assetiq.report_scheduler")

def check_and_generate_reports(db):
    """
    Checks if summary reports for the last 3 days exist.
    If not, generates them.
    """
    site_code = settings.plant_site_code
    now = datetime.utcnow()
    
    # Check last 3 days
    for i in range(1, 4):
        target_date = (now - timedelta(days=i)).date()
        dt_from = datetime.combine(target_date, datetime.min.time())
        dt_to = datetime.combine(target_date, datetime.max.time())
        
        # Check if report already exists for this site and exact date range
        existing = db.execute(
            select(ReportRequest).where(
                ReportRequest.site_code == site_code,
                ReportRequest.report_type == "daily_summary",
                ReportRequest.date_from == dt_from,
                ReportRequest.date_to == dt_to,
                ReportRequest.status == "generated"
            )
        ).scalar_one_or_none()
        
        if not existing:
            log.info(f"Triggering automated summary report for {target_date}")
            try:
                services.report_request_create_and_generate_csv(
                    db,
                    report_type="daily_summary",
                    date_from=dt_from.isoformat(),
                    date_to=dt_to.isoformat(),
                    filters={},
                    actor_user_id="SYSTEM",
                    actor_station_code="WORKER",
                    request_id=f"auto_{target_date.isoformat()}"
                )
                db.commit()
                log.info(f"Automated report for {target_date} generated successfully.")
            except Exception as e:
                db.rollback()
                log.error(f"Failed to generate automated report for {target_date}: {str(e)}")

def run_once():
    db = PlantSessionLocal()
    try:
        check_and_generate_reports(db)
    finally:
        db.close()

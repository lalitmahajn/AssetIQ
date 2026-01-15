import logging
import sys
import uuid
import time
from datetime import datetime

# Setup logging to see output
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger("test_alerts_email")

try:
    from common_core.db import PlantSessionLocal
    from apps.plant_backend.models import EmailQueue
    from apps.plant_worker.email_sender import send_pending
    from apps.plant_worker.critical_alerts import send_critical_alert
except ImportError as e:
    log.error(f"Import failed: {e}. Make sure you are in the project root.")
    sys.exit(1)

def test_email_queue_processing():
    log.info("--- Testing Email Queue Processing ---")
    db = PlantSessionLocal()
    try:
        # 1. Create a dummy email
        test_id = str(uuid.uuid4())
        new_email = EmailQueue(
            to_email="test@example.com",
            subject=f"TEST_SUBJECT_{test_id}",
            body="This is a test email body.",
            status="PENDING",
            created_at_utc=datetime.utcnow(),
            sent_at_utc=None
        )
        db.add(new_email)
        db.commit()
        # We must refresh or obtain the ID to query it later reliably
        db.refresh(new_email) 
        email_id = new_email.id
        log.info(f"Created test email with subject: {new_email.subject}")

        # 2. Run the sender (Runs in its own independent session)
        count = send_pending()
        log.info(f"send_pending() returned count: {count}")

        # 3. Verify
        # CRITICAL: We need to expire our session's cache to see changes made by the other session
        db.expire_all()
        
        refreshed = db.query(EmailQueue).filter(EmailQueue.id == email_id).first()
        
        if refreshed.status == "SENT":
            log.info("SUCCESS: Email status changed to SENT")
        else:
            log.error(f"FAILURE: Email status is {refreshed.status}")
        
        if refreshed.sent_at_utc is not None:
             log.info("SUCCESS: sent_at_utc is populated")
        else:
             log.error("FAILURE: sent_at_utc is None")

    finally:
        db.close()

def test_critical_alerts():
    log.info("\n--- Testing Critical Alerts (SMTP) ---")
    log.info("Attempting to send a critical alert. This is EXPECTED to fail or log an error if SMTP is not configured.")
    
    # We will just run it and observe the logs. The function handles exceptions internally.
    send_critical_alert("TEST CRITICAL ALERT", "This is a test alert body.")
    log.info("Execution completed (check logs above for 'critical_alert' or errors).")

if __name__ == "__main__":
    test_email_queue_processing()
    test_critical_alerts()

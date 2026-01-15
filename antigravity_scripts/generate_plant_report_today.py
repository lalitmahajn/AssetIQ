
import os
from datetime import datetime
from sqlalchemy import select
from common_core.db import PlantSessionLocal
from apps.plant_backend.models import Ticket, TimelineEvent
from common_core.config import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from openpyxl import Workbook

def generate_report():
    print("Generating Report for Today...")
    db = PlantSessionLocal()
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Fetch Data
        stops = db.execute(
            select(TimelineEvent).where(
                TimelineEvent.event_type == "STOP",
                TimelineEvent.occurred_at_utc >= today_start
            )
        ).scalars().all()
        
        tickets = db.execute(
            select(Ticket).where(
                Ticket.created_at_utc >= today_start
            )
        ).scalars().all()
        
        print(f"Found {len(stops)} stops and {len(tickets)} tickets.")

        # Prepare Vault Path
        relative_dir = f"hot/{now.strftime('%Y/%m/%d')}"
        full_dir = os.path.join(settings.report_vault_root, relative_dir)
        os.makedirs(full_dir, exist_ok=True)
        
        stem = f"Plant_Report_{now.strftime('%H%M')}"
        pdf_path = os.path.join(full_dir, f"{stem}.pdf")
        xlsx_path = os.path.join(full_dir, f"{stem}.xlsx")
        
        # PDF Generation
        c = canvas.Canvas(pdf_path, pagesize=A4)
        w, h = A4
        y = h - 50
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, f"AssetIQ Daily Report: {now.date()}")
        y -= 30
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Stops Summary")
        y -= 15
        c.setFont("Helvetica", 10)
        
        total_downtime = 0
        for s in stops:
            dur = s.payload_json.get("duration_seconds", 0)
            reason = s.payload_json.get("reason_code", "Unknown")
            c.drawString(50, y, f"- {s.asset_id}: {reason} ({int(dur/60)} mins)")
            total_downtime += dur
            y -= 12
            
        c.drawString(50, y - 10, f"Total Downtime: {int(total_downtime/60)} mins")
        y -= 40
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Tickets Summary")
        y -= 15
        c.setFont("Helvetica", 10)
        
        for t in tickets:
            c.drawString(50, y, f"- [{t.status}] {t.title} ({t.priority})")
            y -= 12
            
        c.save()
        print(f"PDF Generated: {pdf_path}")
        
        # Excel Generation
        wb = Workbook()
        ws = wb.active
        ws.title = "Stops"
        ws.append(["Asset", "Reason", "Duration (s)", "Occurred At"])
        for s in stops:
            ws.append([s.asset_id, s.payload_json.get("reason_code"), s.payload_json.get("duration_seconds"), s.occurred_at_utc])
            
        ws2 = wb.create_sheet("Tickets")
        ws2.append(["ID", "Title", "Status", "Priority", "Created At"])
        for t in tickets:
            ws2.append([t.id, t.title, t.status, t.priority, t.created_at_utc])
            
        wb.save(xlsx_path)
        print(f"Excel Generated: {xlsx_path}")
        
    finally:
        db.close()

if __name__ == "__main__":
    generate_report()

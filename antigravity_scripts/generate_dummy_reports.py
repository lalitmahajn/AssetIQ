
import os
from datetime import datetime
from common_core.config import settings

def create_dummy_reports():
    # Report Vault Structure: hot/YYYY/MM/DD
    now = datetime.utcnow()
    relative_dir = f"hot/{now.strftime('%Y/%m/%d')}"
    full_dir = os.path.join(settings.report_vault_root, relative_dir)
    
    os.makedirs(full_dir, exist_ok=True)
    
    # Create Dummy PDF
    pdf_path = os.path.join(full_dir, f"Daily_Report_{now.strftime('%H%M')}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n%Dummy PDF Content\n")
    print(f"Created: {pdf_path}")
    
    # Create Dummy Excel
    xlsx_path = os.path.join(full_dir, f"Shift_Log_{now.strftime('%H%M')}.xlsx")
    with open(xlsx_path, "wb") as f:
        f.write(b"PK\x03\x04\nDummy Excel Content")
    print(f"Created: {xlsx_path}")

if __name__ == "__main__":
    create_dummy_reports()

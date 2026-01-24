from common_core.db import PlantSessionLocal
from apps.plant_backend import services
import os

db = PlantSessionLocal()
try:
    print("Testing Report Generation with Custom Name...")

    # Create dummy user if needed or just pass a string ID
    user_id = "test_user_1"

    # 1. Test Daily Summary
    print("Generating Daily Summary...")
    res = services.report_request_create_and_generate_csv(
        db,
        report_type="daily_summary",
        date_from="2026-01-20",
        date_to="2026-01-21",
        filters={},
        custom_name="My_Test_Report_1",
        actor_user_id=user_id,
        actor_station_code=None,
        request_id="req_1",
    )
    print(f"Generated: {res.generated_file_path}")

    # Verify file exists
    vault_root = services.settings.report_vault_root
    full_path = os.path.join(vault_root, res.generated_file_path)
    if os.path.exists(full_path):
        print("✅ File created successfully.")
    else:
        print("❌ File NOT found.")

    # 2. Test Special Chars
    print("\nGenerating with Special Chars...")
    res2 = services.report_request_create_and_generate_csv(
        db,
        report_type="daily_summary",
        date_from="2026-01-20",
        date_to="2026-01-21",
        filters={},
        custom_name="Shift A @ Night!",
        actor_user_id=user_id,
        actor_station_code=None,
        request_id="req_2",
    )
    print(f"Generated: {res2.generated_file_path}")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    db.close()

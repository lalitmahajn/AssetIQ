import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Set dummy env vars for Settings validation
os.environ["JWT_SECRET"] = "dummy"
os.environ["SYNC_HMAC_SECRET"] = "dummy"
os.environ["STATION_SECRET_ENC_KEY"] = "dummy"

from apps.plant_backend.models import Asset, StopQueue
from apps.plant_backend.routers import efficiency


def test_efficiency_logic():
    # Mock Data
    now = datetime.utcnow()
    # Let's say we look at 1 day for simplicity of calculation
    days = 1
    total_minutes = 1 * 24 * 60  # 1440

    # 3 Assets
    # P (Parent)
    # C1 (Critical Child)
    # C2 (Non-Critical Child)

    p = Asset(id="P", name="Parent", is_critical=False, parent_id=None, asset_code="P")
    c1 = Asset(id="C1", name="Child Critical", is_critical=True, parent_id="P", asset_code="C1")
    c2 = Asset(
        id="C2", name="Child Non-Critical", is_critical=False, parent_id="P", asset_code="C2"
    )

    assets = [p, c1, c2]

    # Stops
    # Scenario:
    # 1. C2 (Non-Critical): 10 mins. Should be IGNORED by Parent.
    # 2. P (Parent): 30 mins.
    # 3. C1 (Critical): 20 mins, overlapping P by 10 mins.

    # Timeline relative to 'now'
    # P:   now-60m to now-30m (30m duration)
    # C1:  now-40m to now-20m (20m duration) -> Overlaps P from now-40m to now-30m (10m overlap)
    # C2:  now-100m to now-90m (10m duration) -> Separate

    s1_c2 = StopQueue(
        asset_id="C2",
        opened_at_utc=now - timedelta(minutes=100),
        closed_at_utc=now - timedelta(minutes=90),
    )
    s2_p = StopQueue(
        asset_id="P",
        opened_at_utc=now - timedelta(minutes=60),
        closed_at_utc=now - timedelta(minutes=30),
    )
    s3_c1 = StopQueue(
        asset_id="C1",
        opened_at_utc=now - timedelta(minutes=40),
        closed_at_utc=now - timedelta(minutes=20),
    )

    stops = [s1_c2, s2_p, s3_c1]

    # Mock DB
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_db.execute.return_value = mock_execute

    # The first query is for stops, second for assets
    mock_execute.scalars.return_value.all.side_effect = [stops, assets]

    print("Running efficiency calculation logic Verification...")
    print(
        "Scenario: Parent (30m) overlaps Critical Child (20m) by 10m. Non-Critical Child (10m) separate."
    )

    with patch("apps.plant_backend.routers.efficiency.PlantSessionLocal", return_value=mock_db):
        # Call the function
        result = efficiency.get_efficiency_by_asset(days=days)

        # Verify
        items = {item["asset_id"]: item for item in result["items"]}

        # Check Parent P
        p_stats = items["P"]
        print("\nParent Stats Result:", p_stats)

        # Expected Breakdown:
        # P Downtime + C1 Downtime (Merged)
        # P: [now-60, now-30]
        # C1: [now-40, now-20]
        # Union: [now-60, now-20] -> 40 minutes total duration.

        exp_downtime = 40
        exp_uptime = 1440 - 40
        exp_eff = round((1400 / 1440) * 100, 1)

        if p_stats["downtime_minutes"] == exp_downtime:
            print("✅ SUCCESS: Parent downtime is 40 minutes (Merged correctly).")
        else:
            print(f"❌ FAILURE: Parent downtime {p_stats['downtime_minutes']} != {exp_downtime}")

        # Check C1 (Critical Child)
        c1_stats = items["C1"]
        if c1_stats["downtime_minutes"] == 20:
            print(f"✅ SUCCESS: C1 downtime is {c1_stats['downtime_minutes']} minutes.")
        else:
            print(f"❌ FAILURE: C1 downtime {c1_stats['downtime_minutes']} != 20")

        # Check C2 (Non-Critical Child)
        c2_stats = items["C2"]
        if c2_stats["downtime_minutes"] == 10:
            print(f"✅ SUCCESS: C2 downtime is {c2_stats['downtime_minutes']} minutes.")
        else:
            print(f"❌ FAILURE: C2 downtime {c2_stats['downtime_minutes']} != 10")


if __name__ == "__main__":
    test_efficiency_logic()

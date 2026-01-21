import os
import sys

# Add project root to path
sys.path.append(os.getcwd())


from apps.plant_backend.routers.efficiency import get_efficiency_by_asset


def verify_db():
    print("--- Verifying Efficiency Calculation (Last 7 Days) ---")

    # 1. Run the Algo
    try:
        # We don't need a user object for logic test, mock it or bypass dependency?
        # The function uses `user=Depends(...)`.
        # We can't call the route handler directly strictly because of Depends if we were calling via HTTP.
        # But calling as a python function, `user` is an argument. passing None is fine if not used or we mock.
        # Looking at code: `user` argument is unused in the body!
        result = get_efficiency_by_asset(days=7, user=None)
    except Exception as e:
        print(f"Error calling algorithm: {e}")
        import traceback

        traceback.print_exc()
        return

    items = {i["asset_id"]: i for i in result["items"]}

    # 2. Extract Key Assets
    # HALL-A (Parent)
    # R-101 (Critical Child)
    # C-301 (Non-Critical Child)

    hall_a = items.get("HALL-A")
    r101 = items.get("R-101")
    c301 = items.get("C-301")

    if not hall_a:
        print("HALL-A not found in results.")
        return

    print("\n[Parent] HALL-A:")
    print(f"  Efficiency: {hall_a['efficiency_pct']}%")
    print(f"  Downtime:   {hall_a['downtime_minutes']} min")
    print(f"  Uptime:     {hall_a['uptime_minutes']} min")

    print("\n[Child-Critical] R-101:")
    if r101:
        print(f"  Efficiency: {r101['efficiency_pct']}%")
        print(f"  Downtime:   {r101['downtime_minutes']} min")
    else:
        print("  Not found")

    print("\n[Child-NonCritical] C-301:")
    if c301:
        print(f"  Efficiency: {c301['efficiency_pct']}%")
        print(f"  Downtime:   {c301['downtime_minutes']} min")
    else:
        print("  Not found")

    # 3. Validation Logic
    print("\n--- Logic Validation ---")

    # Check 1: Non-Critical C-301 should NOT contribute to Parent
    # We can't easily 'prove' exclusion just by sum without knowing exact overlaps,
    # but we can check bounds.
    # Parent Downtime <= Sum(Critical Children) + Parent Own.
    # If Parent Downtime > (Sum Critical), that implies Parent had own stops.

    # Let's check specifically for the "Today" injection if we can isolate it?
    # Hard to isolate 'Today' from '7 Days' aggregate without rewriting the query.
    # But we can verify the math consistency.

    total_window = 10080
    calc_uptime = total_window - hall_a["downtime_minutes"]
    calc_eff = round((calc_uptime / total_window) * 100, 1)

    print("Math Check:")
    print(f"  Total Window: {total_window}")
    print(
        f"  Calculated Eff: (({total_window} - {hall_a['downtime_minutes']}) / {total_window}) * 100 = {calc_eff}%"
    )
    print(f"  Reported Eff:   {hall_a['efficiency_pct']}%")

    if abs(calc_eff - hall_a["efficiency_pct"]) < 0.1:
        print("  ✅ Efficiency % matches Downtime minutes.")
    else:
        print("  ❌ Efficiency % mismatch.")


if __name__ == "__main__":
    verify_db()

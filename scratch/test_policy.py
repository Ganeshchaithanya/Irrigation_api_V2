import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.plugins.meta.policy import apply_policy_rules

def run_tests():
    # Base mock decision
    decision_in = {
        "decision": "NORMAL_IRRIGATION",
        "confidence": 0.95
    }
    
    print("--- RUNNING POLICY VETO CHECKS ---")
    
    # Scenario 1: Inside Allowed Morning Hour (7 AM), moisture is dry (30% vs target 40%)
    res1 = apply_policy_rules(
        decision=decision_in,
        rain_mm=0.0,
        trust_score=0.9,
        last_irrigation_hours_ago=24.0,
        hour_of_day=7,
        current_moisture=30.0,
        predicted_moisture_6h=28.0,
        target_moisture_min=40.0
    )
    print(f"\n[Test 1] 7 AM, Moisture 30% (Target 40%):")
    print(f"  Decision: {res1.get('decision')}")
    print(f"  Action Now: {res1.get('action_now')}")
    print(f"  Applied Now MM: {res1.get('applied_now_mm')}")
    print(f"  Applied Now Liters: {res1.get('applied_now_liters')}")
    print(f"  Reasons: {res1.get('policy_reason')}")
    assert res1.get("action_now") == "IRRIGATE", "Test 1 failed: Should have irrigated!"

    # Scenario 2: Outside Allowed Hours (13 PM / 1:00 PM), moisture is dry (30% vs target 40%)
    res2 = apply_policy_rules(
        decision=decision_in,
        rain_mm=0.0,
        trust_score=0.9,
        last_irrigation_hours_ago=24.0,
        hour_of_day=13,
        current_moisture=30.0,
        predicted_moisture_6h=28.0,
        target_moisture_min=40.0
    )
    print(f"\n[Test 2] 1 PM (Outside hours), Moisture 30% (Target 40%):")
    print(f"  Decision: {res2.get('decision')}")
    print(f"  Action Now: {res2.get('action_now')}")
    print(f"  Reasons: {res2.get('policy_reason')}")
    assert res2.get("action_now") == "SKIP", "Test 2 failed: Should have skipped due to hours!"
    assert any("falls outside standard automated windows" in r for r in res2.get("policy_reason")), "Test 2 failed: Reason missing!"

    # Scenario 3: Inside Allowed Morning Hour (7 AM), moisture is wet (45% vs target 40%)
    res3 = apply_policy_rules(
        decision=decision_in,
        rain_mm=0.0,
        trust_score=0.9,
        last_irrigation_hours_ago=24.0,
        hour_of_day=7,
        current_moisture=45.0,
        predicted_moisture_6h=43.0,
        target_moisture_min=40.0
    )
    print(f"\n[Test 3] 7 AM, Moisture 45% (Target 40%):")
    print(f"  Decision: {res3.get('decision')}")
    print(f"  Action Now: {res3.get('action_now')}")
    print(f"  Reasons: {res3.get('policy_reason')}")
    assert res3.get("action_now") == "SKIP", "Test 3 failed: Should have skipped due to sufficient moisture!"
    assert any("is above target threshold" in r for r in res3.get("policy_reason")), "Test 3 failed: Reason missing!"

    print("\n--- ALL POLICY VETO TESTS PASSED SUCCESSFULLY! ---")

if __name__ == "__main__":
    run_tests()

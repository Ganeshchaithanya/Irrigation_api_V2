import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Mock the settings and logger for clean test outputs
class MockSettings:
    DRIFT_PENALTY_TRUST_SCORE = 0.5
    TRUST_RECOVERY_RATE = 0.05
    SOIL_HOLD_FACTOR = {"loam": 0.18}
    IRRIGATION_RESPONSE_TOLERANCE_PCT = 0.3

# Import our actual perception logic
from backend.core.reliability.perception import calculate_weighted_fusion

def run_virtual_sensing_verification():
    print("=" * 60)
    print("   AQUASOL V2 — VIRTUAL SENSING VALIDATION ENGINE")
    print("=" * 60)

    # Test Case 1: Healthy Node State (Full Trust)
    sensor_moisture = 32.5
    predicted_moisture = 40.0
    healthy_trust = 1.0

    healthy_fused = calculate_weighted_fusion(
        sensor_moisture=sensor_moisture,
        predicted_moisture=predicted_moisture,
        trust_score=healthy_trust
    )
    print(f"\n[Test 1] Healthy Node Check:")
    print(f"  • Physical Sensor Moisture : {sensor_moisture}%")
    print(f"  • AI Model Predicted      : {predicted_moisture}%")
    print(f"  • Sensor Trust Score       : {healthy_trust}")
    print(f"  • Resulting Fused Moisture : {healthy_fused}% (Uses 100% Physical Reading)")
    assert healthy_fused == sensor_moisture, "Failed Healthy fusion assert!"

    # Test Case 2: Sensor Drift State (Partial Trust Correction)
    drift_trust = 0.60
    drift_fused = calculate_weighted_fusion(
        sensor_moisture=sensor_moisture,
        predicted_moisture=predicted_moisture,
        trust_score=drift_trust
    )
    expected_drift = round((sensor_moisture * 0.6) + (predicted_moisture * 0.4), 2)
    print(f"\n[Test 2] Sensor Drift Self-Correction Check:")
    print(f"  • Physical Sensor Moisture : {sensor_moisture}%")
    print(f"  • AI Model Predicted      : {predicted_moisture}%")
    print(f"  • Sensor Trust Score       : {drift_trust} (Reduced due to drift detection)")
    print(f"  • Resulting Fused Moisture : {drift_fused}% (Corrected: expects {expected_drift}%)")
    assert drift_fused == expected_drift, "Failed Drift fusion assert!"

    # Test Case 3: Offline Node / Hardware Failure (VIRTUAL SENSING ACTIVE)
    # The device hasn't checked in for > 5 minutes, backend sets trust to 0.0
    failed_trust = 0.0
    dead_sensor_value = 0.0 # Offline/unplugged probe reading zero

    virtual_sensing_fused = calculate_weighted_fusion(
        sensor_moisture=dead_sensor_value,
        predicted_moisture=predicted_moisture,
        trust_score=failed_trust
    )
    print(f"\n[Test 3] Critical Node Failure / Virtual Sensing Takeover:")
    print(f"  • Unplugged Probe Reading : {dead_sensor_value}% (Faulty / Zero)")
    print(f"  • AI Model Predicted      : {predicted_moisture}%")
    print(f"  • Sensor Trust Score       : {failed_trust} (CRITICAL: Node offline alert triggered!)")
    print(f"  • Resulting Fused Moisture : {virtual_sensing_fused}% (FAILOVER: Uses 100% AI Prediction)")
    assert virtual_sensing_fused == predicted_moisture, "Failed Virtual Sensing takeover assert!"

    print("\n" + "=" * 60)
    print("  SUCCESS: VIRTUAL SENSING FAILOVER MECHANISM IS 100% OPERATIONAL!")
    print("=" * 60)

if __name__ == "__main__":
    run_virtual_sensing_verification()

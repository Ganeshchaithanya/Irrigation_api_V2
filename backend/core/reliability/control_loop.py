"""
Control — Closed-Loop Control Module
Evaluates telemetry *during* an active irrigation cycle.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.utils.logger import logger
from backend.config.settings import get_settings

settings = get_settings()

def evaluate_mid_cycle(
    zone_state: Dict[str, Any],
    current_moisture: float,
    soil_type: str = "loam",
    grace_period_minutes: int = 15
) -> Dict[str, Any]:
    """
    Evaluates telemetry received while a valve is actively open.
    Returns dictates on whether to 'stop' early or abort due to physical failure.
    """
    valve_start_time = zone_state.get("last_irrigation_at")
    basline_moisture = zone_state.get("moisture_at_irrigation_start")
    target_moisture = zone_state.get("target_moisture_max", 80.0) # Assume upper bound
    expected_gain_mm = zone_state.get("expected_gain_mm", 0.0)
    
    if not valve_start_time or basline_moisture is None:
        return {"action": "continue", "confidence": 1.0}

    now = datetime.now(timezone.utc)
    elapsed_minutes = (now - valve_start_time).total_seconds() / 60.0

    # 1. EARLY STOP LOGIC (Goal Reached)
    if current_moisture >= target_moisture:
        logger.info(f"[control_loop] Target moisture reached ({current_moisture}% >= {target_moisture}%). Triggering early stop.")
        return {
            "action": "early_stop",
            "reason": "target_reached",
            "confidence": 1.0
        }

    # 2. FLOW ANOMALY DETECTION (Delivery Rate)
    # We expect moisture to rise over time while valve is open.
    # Wait for grace period to allow water to percolate.
    if elapsed_minutes < grace_period_minutes:
        return {"action": "continue", "confidence": 1.0, "reason": "grace_period"}

    actual_gain = current_moisture - basline_moisture
    # Rough estimation: If 15+ minutes have passed, we expect at least some positive movement.
    # We can calculate an expected rate based on mm applied, but for mid-cycle:
    # If the reading hasn't moved at all, or dropped, something is wrong.
    
    # Example heuristic: Expect at least 0.5% gain per 15 minutes of active flow
    expected_minimum_gain = (elapsed_minutes / 15.0) * 0.5

    if actual_gain < expected_minimum_gain:
        confidence = max(0.1, 1.0 - (expected_minimum_gain - max(0, actual_gain)))
        
        # If it's critically failing (e.g. 0 gain after 30 mins) -> abort
        if elapsed_minutes > 30 and actual_gain <= 0:
            logger.error(f"[control_loop] FLOW FAILURE: Valve open {elapsed_minutes:.1f}m but gain is {actual_gain}%. Aborting.")
            return {
                "action": "abort_flow_failure",
                "reason": "mid_cycle_flow_issue",
                "confidence": 0.1
            }
        
        return {"action": "continue", "confidence": round(confidence, 2), "reason": "low_flow_rate"}

    return {"action": "continue", "confidence": 1.0, "reason": "flow_optimal"}

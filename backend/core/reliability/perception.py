"""
Core Reliability — Perception Intelligence
Implements self-correcting perception, weighted fusion, and drift validation.
"""
from typing import Dict, Any, Optional
from backend.utils.logger import logger
from backend.config.settings import get_settings

settings = get_settings()

def calculate_weighted_fusion(
    sensor_moisture: float,
    predicted_moisture: float,
    trust_score: float
) -> float:
    """
    Weighted Perception Fusion: 
    fused = (sensor * trust) + (predicted * (1 - trust))
    Handles the 'Virtual Sensing' gracefully instead of binary switching.
    """
    # Clip trust to valid range
    trust = max(0.0, min(1.0, trust_score))
    fused = (sensor_moisture * trust) + (predicted_moisture * (1 - trust))
    return round(fused, 2)


def detect_slow_drift(
    current_moisture: float,
    rolling_avg_24h: Optional[float],
) -> Dict[str, Any]:
    """
    Detects cumulative 'Slow Drift' (believable steps that lead to false deficits).
    """
    if rolling_avg_24h is None:
        return {"is_anomaly": False}

    deviation = abs(float(current_moisture) - float(rolling_avg_24h))
    
    if deviation > settings.SLOW_DRIFT_THRESHOLD_PCT:
        return {
            "is_anomaly": True,
            "reason": "slow_drift_detected",
            "details": f"Reading {current_moisture}% deviates {deviation:.1f}% from 24h baseline ({rolling_avg_24h}%)."
        }
    
    return {"is_anomaly": False}


def validate_irrigation_gain(
    actual_gain_pct: float,
    mm_applied: float,
    soil_type: str,
    root_depth: float,
    efficiency: float = 0.9
) -> Dict[str, Any]:
    """
    Reality Check: Did the sensor increase as much as the applied water predicted?
    Returns { is_valid, expected_gain, deviation }
    """
    # Physics: Gain (%) = (net_water_mm) / (soil_factor * depth_mm) * 100
    soil_factor = settings.SOIL_HOLD_FACTOR.get(soil_type, 0.18)
    expected_gain = (mm_applied * efficiency) / (soil_factor * root_depth) * 100
    
    # Tolerance Check
    # If we apply water but sensor hardly moves (e.g., gain < 30% of expected) → Delivery or Sensor Issue.
    min_threshold = expected_gain * settings.IRRIGATION_RESPONSE_TOLERANCE_PCT
    
    is_valid = actual_gain_pct >= min_threshold
    
    return {
        "is_valid": is_valid,
        "expected_gain": round(expected_gain, 2),
        "actual_gain": round(actual_gain_pct, 2),
        "deviation": round(expected_gain - actual_gain_pct, 2)
    }


def correlate_zones(
    target_zone_id: str,
    target_trend: float,
    neighbors: list # list of {zone_id, trend, soil_type}
) -> Dict[str, Any]:
    """
    Cross-Zone Correlation Check:
    If Zone A drops 12% more than its peer (Zone B) under same weather/soil, suspect anomaly.
    """
    if not neighbors:
        return {"is_correlated": True} # Default to true if alone
        
    for peer in neighbors:
        # Simple trend delta check
        delta = abs(target_trend - peer.get("trend", 0.0))
        if delta > settings.CORRELATION_THRESHOLD_PCT:
            return {
                "is_correlated": False,
                "reason": "correlation_violation",
                "details": f"Zone delta ({delta:.1f}%) exceeds correlation threshold vs {peer.get('zone_id')}."
            }
            
    return {"is_correlated": True}

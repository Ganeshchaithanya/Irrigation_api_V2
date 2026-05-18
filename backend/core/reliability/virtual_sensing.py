"""
Core Reliability — Virtual Sensing
Estimates missing sensor values using peer nodes and historical averages.
"""
from typing import List, Optional
import statistics
from backend.utils.logger import logger


def compute_virtual_moisture(
    peer_readings: List[float],
    zone_correction_factor: float = 1.0,
) -> Optional[float]:
    """
    moisture_virtual = mean(peer_nodes_same_zone) * zone_correction_factor
    """
    if not peer_readings:
        return None
    zone_mean = statistics.mean(peer_readings)
    virtual = round(zone_mean * zone_correction_factor, 2)
    logger.info(f"[virtual] Peer mean={zone_mean:.1f}, correction={zone_correction_factor:.3f} → virtual={virtual}")
    return virtual


def compute_zone_correction_factor(
    historical_avg_this_node: float,
    historical_avg_zone: float,
) -> float:
    """
    zone_correction_factor = historical_avg_this_node / historical_avg_zone
    Returns 1.0 on division by zero.
    """
    if historical_avg_zone == 0:
        return 1.0
    return round(historical_avg_this_node / historical_avg_zone, 4)


def select_virtual_value(
    peer_readings: List[float],
    zone_correction_factor: float,
    lstm_prediction: Optional[float] = None,
) -> dict:
    """
    Returns the best virtual estimate with method used.
    Priority: peer mean > LSTM prediction.
    """
    if peer_readings:
        val = compute_virtual_moisture(peer_readings, zone_correction_factor)
        return {"value": val, "method": "peer_mean", "source": "virtual"}

    if lstm_prediction is not None:
        logger.info(f"[virtual] No peers — using LSTM prediction={lstm_prediction}")
        return {"value": lstm_prediction, "method": "lstm_fallback", "source": "virtual"}

    return {"value": None, "method": "none", "source": "missing"}

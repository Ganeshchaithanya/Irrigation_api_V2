"""
Core Reliability — Sensor Trust Engine
Implements the formula:
  trust = 0.4*(1-anomaly_rate) + 0.3*consistency + 0.2*uptime + 0.1*recency
"""
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import statistics
from backend.utils.logger import logger

# Sensor physical range reference (for consistency normalization)
SENSOR_RANGES = {
    "soil_moisture": 100.0,
    "temperature": 70.0,
    "humidity": 100.0,
}


def compute_trust_score(
    anomaly_rate_7d: float,         # anomalies_last_7d / total_readings_7d
    last_10_readings: List[float],  # raw moisture values
    uptime_score_7d: float,         # packets_received / expected_packets
    last_seen: Optional[datetime],  # last timestamp from node
    sensor_key: str = "soil_moisture",
) -> dict:
    """
    Returns dict with trust_score and component scores.
    """
    # Component 1: anomaly component
    anomaly_component = 0.4 * (1.0 - min(anomaly_rate_7d, 1.0))

    # Component 2: consistency (1 - std/range)
    if len(last_10_readings) >= 2:
        std = statistics.stdev(last_10_readings)
        sensor_range = SENSOR_RANGES.get(sensor_key, 100.0)
        consistency_score = max(0.0, 1.0 - (std / sensor_range))
    else:
        consistency_score = 0.5  # neutral when not enough data

    consistency_component = 0.3 * consistency_score

    # Component 3: uptime
    uptime_component = 0.2 * min(uptime_score_7d, 1.0)

    # Component 4: recency (1 if seen < 10 min ago)
    if last_seen:
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        minutes_ago = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60
        recency_score = 1.0 if minutes_ago < 10 else 0.0
    else:
        recency_score = 0.0

    recency_component = 0.1 * recency_score

    trust_score = round(
        anomaly_component + consistency_component + uptime_component + recency_component,
        4
    )

    return {
        "trust_score": trust_score,
        "anomaly_component": round(anomaly_component, 4),
        "consistency_score": round(consistency_score, 4),
        "uptime_score": round(uptime_score_7d, 4),
        "recency_score": recency_score,
        "use_virtual_sensing": trust_score < 0.5,
    }


def batch_trust_scores(nodes_data: List[dict]) -> List[dict]:
    """
    Compute trust scores for a list of node data dicts.
    Each dict must have: anomaly_rate_7d, last_10_readings,
    uptime_score_7d, last_seen.
    """
    results = []
    for nd in nodes_data:
        score = compute_trust_score(
            anomaly_rate_7d=nd.get("anomaly_rate_7d", 0.0),
            last_10_readings=nd.get("last_10_readings", []),
            uptime_score_7d=nd.get("uptime_score_7d", 1.0),
            last_seen=nd.get("last_seen"),
        )
        score["node_id"] = nd.get("node_id")
        results.append(score)
    return results

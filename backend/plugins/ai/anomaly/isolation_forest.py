"""
AI Plugin — Anomaly Detection
Thin facade over core/reliability/anomaly.py.
Exposes:
  - load_anomaly_model()
  - detect_anomaly(...)
  - get_anomaly_summary(results)   ← new helper for API/alerts layer
"""
from backend.core.reliability.anomaly import (
    load_anomaly_model,
    detect_anomaly,
    ANOMALY_TYPES,
    SEVERITY_MAP,
)
from typing import List, Dict, Any


def get_anomaly_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate multiple zone anomaly results into a single farm-level summary.
    Returns the highest severity event and a count breakdown.
    """
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, None: 0}
    breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0, "normal": 0}

    worst_severity = None
    worst_event = None

    for r in results:
        sev = r.get("severity")
        if r.get("is_anomaly"):
            bucket = sev if sev in breakdown else "low"
            breakdown[bucket] += 1
            if severity_rank.get(sev, 0) > severity_rank.get(worst_severity, 0):
                worst_severity = sev
                worst_event = r
        else:
            breakdown["normal"] += 1

    return {
        "anomaly_count": sum(v for k, v in breakdown.items() if k != "normal"),
        "worst_severity": worst_severity,
        "worst_event": worst_event,
        "breakdown": breakdown,
    }


__all__ = [
    "load_anomaly_model",
    "detect_anomaly",
    "get_anomaly_summary",
    "ANOMALY_TYPES",
    "SEVERITY_MAP",
]

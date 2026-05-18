"""
Control — Command Builder
Builds structured ESP32 command payloads.
"""
from typing import Dict, Any
from datetime import datetime, timezone


def build_irrigate_command(
    zone_id: str,
    duration_min: float,
    target_moisture: float,
    decision_id: str,
    cycles: int = 1,
    soak_time_min: int = 0
) -> Dict[str, Any]:
    return {
        "cmd": "valve_on",
        "zone_id": zone_id,
        "duration_sec": int(duration_min * 60),
        "cycles": cycles,
        "soak_min": soak_time_min,
        "target_moisture": target_moisture,
        "decision_id": str(decision_id),
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }


def build_stop_command(zone_id: int, reason: str = "manual") -> Dict[str, Any]:
    return {
        "cmd": "valve_off",
        "zone_id": zone_id,
        "reason": reason,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }


def build_query_command(zone_id: int) -> Dict[str, Any]:
    return {
        "cmd": "status_query",
        "zone_id": zone_id,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }

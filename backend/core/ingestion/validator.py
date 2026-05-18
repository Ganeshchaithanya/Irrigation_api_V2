"""
Core Ingestion — Validator
Lightweight physical range and completeness checks on parsed node events.
"""
from typing import Optional
from backend.core.ingestion.parser import ParsedNodeEvent
from backend.utils.logger import logger

# Physical sensor limits
LIMITS = {
    "soil_moisture": (0.0, 100.0),
    "temperature":   (-10.0, 60.0),
    "humidity":      (0.0, 100.0),
    "battery_voltage": (0.0, 5.0),
}


def validate_event(event: ParsedNodeEvent) -> tuple[bool, str]:
    """
    Returns (is_valid, reason).
    An invalid event should NOT be stored — flag instead.
    """
    # Check MAC format
    if not event.mac_address or len(event.mac_address) < 8:
        return False, "invalid_mac"

    # Check at least one sensor has a value
    has_data = any([
        event.soil_moisture is not None,
        event.temperature is not None,
        event.humidity is not None,
    ])
    if not has_data:
        return False, "all_sensors_null"

    # Check each value against physical limits
    for field, (lo, hi) in LIMITS.items():
        val = getattr(event, field, None)
        if val is not None and not (lo <= val <= hi):
            logger.warning(f"[validator] {event.node_label}.{field}={val} out of range [{lo},{hi}]")
            return False, f"{field}_out_of_range"

    return True, "ok"


def validate_events(events: list) -> tuple[list, list]:
    """
    Split events list into (valid_events, invalid_events).
    """
    valid, invalid = [], []
    for ev in events:
        ok, reason = validate_event(ev)
        if ok:
            valid.append(ev)
        else:
            invalid.append((ev, reason))
    return valid, invalid

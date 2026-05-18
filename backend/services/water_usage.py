"""
Service — Water Usage Calculator
Computes water consumed per irrigation session.
"""
from typing import Optional


def compute_water_used(
    duration_min: float,
    flow_rate_lpm: float = 10.0,   # litres per minute (default drip system)
    area_acres: float = 1.0,
) -> dict:
    """
    Returns: { total_liters, per_acre_liters, duration_min }
    """
    total_liters = duration_min * flow_rate_lpm
    per_acre = round(total_liters / max(area_acres, 0.01), 2)
    return {
        "total_liters": round(total_liters, 2),
        "per_acre_liters": per_acre,
        "duration_min": duration_min,
        "flow_rate_lpm": flow_rate_lpm,
    }


def compute_water_stress_index(
    days_below_target: int,
    severity_factor: float = 1.0,
) -> float:
    """
    Water stress index = days successive below target × severity.
    Capped at 10.
    """
    return round(min(days_below_target * severity_factor, 10.0), 2)

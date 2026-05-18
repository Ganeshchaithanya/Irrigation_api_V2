"""
Core Spatial — Root-Zone Estimator
Calculates estimated root moisture based on surface soil measurements,
temperature constraints, and depth mismatches.
"""
import math
from typing import Dict, Any

def detect_depth_mismatch(sensor_depth_cm: int, root_depth_cm: int) -> bool:
    """Flags if the sensor is too shallow to assess the primary root zone."""
    if root_depth_cm <= 0:
        return False
    return sensor_depth_cm < (0.3 * root_depth_cm)


def estimate_root_moisture(
    surface_moisture: float, 
    soil_type: str, 
    temp_celsius: float
) -> float:
    """
    Transforms surface reading into root-zone estimation.
    Applies temperature-driven evaporative decay and soil infiltration limits.
    """
    soil_key = soil_type.lower().replace(" ", "_")
    
    # Clay traps water on top, giving falsely high surface reads when dry below
    if "clay" in soil_key:
        attenuation = 0.65
    else:
        attenuation = 0.80
        
    # High temp severely dries out the profile under the surface crust
    temp_factor = 1.0 - (min(temp_celsius, 100.0) / 100.0)
    
    estimated_root = surface_moisture * attenuation * temp_factor
    return round(float(estimated_root), 2)

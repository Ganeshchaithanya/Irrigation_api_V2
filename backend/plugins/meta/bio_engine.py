"""
AquaSol — Physics-Aware Biological Engine
Shared constants and functions used by all dataset generators.
Based on FAO-56 methodology + RRC (Recovery Rate Controller).
"""
import math, random, json
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────
# CROP SENSITIVITY PROFILES (settings.py equivalent)
# Based on FAO-56 Kc values + agronomic literature
# ─────────────────────────────────────────────────────────────
"""
AquaSol — Physics-Aware Biological Engine
Pure math library for FAO-56 methodology + Recovery Rate Controller.
Crop profiles are now dynamically loaded from the database and cached.
"""
import math, time
from typing import Optional, Dict

class CropProfileLoader:
    _cache = {}
    _cache_ttl_seconds = 300 # 5 minutes

    @classmethod
    async def get_profile(cls, db_session, crop_name: str) -> Optional[Dict]:
        """Fetch crop biological profile from DB with short-TTL cache."""
        now = time.time()
        # Cache hit
        if crop_name in cls._cache:
            profile_data, timestamp = cls._cache[crop_name]
            if now - timestamp < cls._cache_ttl_seconds:
                return profile_data
                
        # Cache miss or expired
        from sqlalchemy import select
        from backend.models.crop import CropBioProfile
        
        # We capitalize crop_name to match DB cleanly, but query using ILIKE or standard
        stmt = select(CropBioProfile).where(CropBioProfile.name.ilike(crop_name))
        result = await db_session.execute(stmt)
        record = result.scalar_one_or_none()
        
        if not record:
            return None
            
        # Reconstruct into the exact Python dict shape expected by the math engine
        stages_tuples = [(s["name"], s["start"], s["end"], s["min_m"], s["max_m"]) for s in record.stages_json]
        
        profile_dict = {
            "name": record.name,
            "season": record.season,
            "duration": record.duration_days,
            "water_req_mm": record.water_req_mm,
            "osmotic_shock_sensitive": record.osmotic_shock_sensitive,
            "rrc_max_mm_per_cycle": float(record.rrc_max_mm_per_cycle),
            "rrc_stage_split": record.rrc_stage_split,
            "temp_stress_threshold_c": float(record.temp_stress_threshold_c),
            "temp_optimal_c": (float(record.temp_optimal_min_c), float(record.temp_optimal_max_c)),
            "tsi_threshold": float(record.tsi_threshold),
            "kc": record.kc_json,
            "stages": stages_tuples,
            "soil_type": record.soil_type
        }
        
        # Save to cache
        cls._cache[crop_name] = (profile_dict, now)
        return profile_dict

# ─────────────────────────────────────────────────────────────
# BIOLOGICAL ENGINE FUNCTIONS (Pure Math)
# ─────────────────────────────────────────────────────────────

def get_kc(profile: dict, dap: int) -> float:
    """Dynamic Kc based on crop stage position. FAO-56 curve."""
    duration = profile["duration"]
    kc_vals = profile["kc"]
    frac = dap / duration
    if frac < 0.15:   return kc_vals["initial"]
    elif frac < 0.35: return kc_vals["initial"] + (kc_vals["development"] - kc_vals["initial"]) * ((frac-0.15)/0.20)
    elif frac < 0.65: return kc_vals["mid"]
    elif frac < 0.85: return kc_vals["mid"] + (kc_vals["late"] - kc_vals["mid"]) * ((frac-0.65)/0.20)
    else:             return kc_vals["harvest"]

def compute_vpd(temp_c: float, humidity_pct: float) -> float:
    """Vapor Pressure Deficit (kPa) — simplified Magnus equation."""
    es = 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    ea = es * (humidity_pct / 100.0)
    return round(max(0.0, es - ea), 4)

def compute_etc(temp_c: float, humidity_pct: float, kc: float,
                solar_radiation_mj: float = None) -> float:
    """ETc (mm/h) — Pseudo-Penman Monteith via VPD + empirical solar."""
    vpd = compute_vpd(temp_c, humidity_pct)
    if solar_radiation_mj is None:
        solar_radiation_mj = max(5, 20 - abs(temp_c - 25) * 0.3)
    eto_h = (0.408 * vpd * solar_radiation_mj * 0.0416) + (0.0023 * max(0, temp_c - 5) * vpd)
    etc_h = eto_h * kc
    return round(max(0.0, etc_h), 4)

def compute_tsi(temp_c: float, humidity_pct: float) -> float:
    """Thermal Stress Index — combines heat and humidity burden on canopy."""
    vpd = compute_vpd(temp_c, humidity_pct)
    tsi = temp_c * (1 + 0.33 * (humidity_pct / 100)) + vpd * 2.5
    return round(tsi, 2)

def get_stage_for_dap(profile: dict, dap: int) -> tuple:
    """Return (stage_name, moisture_min, moisture_max) for given DAP."""
    for stage_name, ds, de, mmin, mmax in profile["stages"]:
        if ds <= dap <= de:
            return stage_name, mmin, mmax
    last = profile["stages"][-1]
    return last[0], last[3], last[4]

def compute_rrc(profile: dict, deficit_mm: float,
                temp_c: float, is_sensitive: bool) -> dict:
    """Recovery Rate Controller — prevents osmotic shock."""
    max_per_cycle = profile["rrc_max_mm_per_cycle"]
    if temp_c > profile["temp_stress_threshold_c"]:
        heat_factor = 1 - (temp_c - profile["temp_stress_threshold_c"]) * 0.02
        max_per_cycle = max_per_cycle * max(0.4, heat_factor)

    if not is_sensitive or deficit_mm <= max_per_cycle:
        return {
            "apply_now_mm": round(deficit_mm, 2),
            "recovery_plan": [],
            "staged": False
        }

    apply_now = min(deficit_mm * 0.4, max_per_cycle * 0.45)
    remaining = deficit_mm - apply_now
    eve_split, morn_split = profile["rrc_stage_split"]
    return {
        "apply_now_mm": round(apply_now, 2),
        "recovery_plan": [
            {"window": "evening", "mm": round(remaining * eve_split, 2)},
            {"window": "next_morning", "mm": round(remaining * morn_split, 2)},
        ],
        "staged": True
    }

def liters_from_mm(mm: float, area_acres: float) -> int:
    return int(round(mm * area_acres * 4047))

def get_operational_mode(temp_c: float, profile: dict, deficit_mm: float,
                          rain_prob: float, current_moisture: float,
                          tgt_min: float, tgt_max: float) -> str:
    tsi = compute_tsi(temp_c, 60)
    if temp_c >= profile["temp_stress_threshold_c"] and tsi > profile["tsi_threshold"]:
        return "THERMAL_MITIGATION_MODE"
    if rain_prob > 0.70:
        return "RAIN_ANTICIPATION_MODE"
    if current_moisture < tgt_min - 15:
        return "DEFICIT_RECOVERY"
    if current_moisture > tgt_max + 10:
        return "EXCESS_MOISTURE"
    if tgt_min <= current_moisture <= tgt_max:
        return "OPTIMAL_RANGE"
    if current_moisture < tgt_min:
        return "MILD_DEFICIT"
    return "STANDARD"

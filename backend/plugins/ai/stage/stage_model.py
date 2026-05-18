"""
AI Plugin — Stage Awareness (v2)
Three-tier inference chain:
  1. XGBoost supervised classifier  (trained on 77k bio-dataset with labeled stages)
  2. KMeans unsupervised clustering  (legacy, per-crop pkl)
  3. Rule-based DAP lookup           (season JSON, always available)

New outputs vs v1:
  - growth_progress_pct  : 0-100 % through total crop cycle
  - kc                   : crop coefficient for the predicted stage
  - stage_sensitivity    : bool — is this a water-sensitive stage?
  - calibrated_confidence: probability from XGBoost, not distance-based
"""
import os
import json
import joblib
import numpy as np
from typing import Optional, Dict, Any
from backend.config.settings import get_settings
from backend.utils.logger import logger

settings = get_settings()

# ── Model caches ─────────────────────────────────────────────────────────────
# Season JSON
_season_data: Dict[str, Any] = {}


# ── Startup loaders ───────────────────────────────────────────────────────────

def _load_season_data():
    global _season_data
    data_dir = settings.DATA_DIR
    for season in ["kharif", "rabi", "zaid"]:
        path = os.path.join(data_dir, f"{season}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _season_data[season] = json.load(f)
            logger.info(f"[stage] Loaded {season}.json")
        except Exception as e:
            logger.warning(f"[stage] Could not load {season}.json: {e}")


def load_stage_models():
    """Load all stage datasets at startup. Called by app lifespan."""
    _load_season_data()
    logger.info("[stage] Ready — Rule-based engine initialized.")


# ── Main inference ────────────────────────────────────────────────────────────

def predict_stage(
    crop: str,
    season: str,
    days_after_planting: int,
    soil_moisture_avg_24h: float,
    total_duration_days: int = 150,
) -> Dict[str, Any]:
    """
    Predict current crop growth stage using deterministic rules + moisture correction.

    Returns:
      {
        stage                : str,
        soil_moisture        : str,    # e.g. "70-85"
        irrigation           : str,    # e.g. "Every 3-5 days"
        effective_dap        : int,
        correction_applied   : int,
        kc                   : float,
        stage_sensitivity    : bool,
        target_moisture_min  : float,
        target_moisture_max  : float,
        method               : str,    # "rule_based" | "fallback"
        status               : str,
      }
    """
    # ── Tier 1: Initial Lookup for target moisture ───────────────────────────
    # We need to know the target moisture of the 'intended' stage to decide on correction
    raw_stage = _lookup_raw_stage(crop, season, days_after_planting)
    target_min = raw_stage.get("target_moisture_min", 50.0)

    # ── Tier 2: Correction Layer ─────────────────────────────────────────────
    # If soil_moisture too low: delay stage progression
    effective_dap = days_after_planting
    correction = 0

    if soil_moisture_avg_24h < target_min - 5:
        # Penalize DAP based on moisture deficit
        # Every 5% deficit beyond the buffer adds 1 day of biological delay
        deficit = (target_min - 5) - soil_moisture_avg_24h
        correction = -min(10, int(deficit / 5) + 1)
        effective_dap = max(0, days_after_planting + correction)
        logger.info(f"[stage] Moisture stress detected ({soil_moisture_avg_24h}% < {target_min}%). Delaying DAP by {correction} days.")

    # ── Tier 3: Final Lookup with Effective DAP ──────────────────────────────
    result = _rule_based_stage(crop, season, effective_dap)
    
    # Add correction metadata
    result["effective_dap"] = effective_dap
    result["correction_applied"] = correction
    result["real_dap"] = days_after_planting
    
    return result


def _lookup_raw_stage(crop: str, season: str, dap: int) -> Dict[str, Any]:
    """Internal helper to get stage without correction to find thresholds."""
    return _rule_based_stage(crop, season, dap)


# ── Tier implementations ──────────────────────────────────────────────────────

def _rule_based_stage(crop: str, season: str, dap: int) -> Dict[str, Any]:
    """Lookup stage from kharif/rabi/zaid.json growth_stages array."""
    season_data = _season_data.get(season.lower(), {})
    crops_list = season_data.get("crops", [])

    for c in crops_list:
        if c.get("name", "").lower() == crop.lower():
            for stage in c.get("growth_stages", []):
                if stage["days_start"] <= dap <= stage["days_end"]:
                    stage_name = stage["stage"]
                    kc, sensitive = _get_stage_kc_sensitivity(crop, stage_name)
                    m_min = stage.get("soil_moisture_min", 50)
                    m_max = stage.get("soil_moisture_max", 70)
                    
                    return {
                        "stage": stage_name,
                        "soil_moisture": f"{m_min}-{m_max}",
                        "irrigation": stage.get("irrigation_frequency", "As needed"),
                        "kc": kc,
                        "stage_sensitivity": sensitive,
                        "target_moisture_min": float(m_min),
                        "target_moisture_max": float(m_max),
                        "method": "rule_based",
                        "status": "success",
                    }

    # Total fallback
    kc, sensitive = _get_stage_kc_sensitivity(crop, "vegetative")
    return {
        "stage": "vegetative",
        "soil_moisture": "50-70",
        "irrigation": "Every 7-10 days",
        "kc": kc,
        "stage_sensitivity": sensitive,
        "target_moisture_min": 50.0,
        "target_moisture_max": 70.0,
        "method": "fallback",
        "status": "no_match",
    }


# ── Agronomic helpers ─────────────────────────────────────────────────────────

def _get_stage_kc_sensitivity(crop: str, stage: str):
    """
    Return (kc, is_sensitive) for a crop+stage pair.
    """
    crop_key = crop.lower()
    profiles = settings.CROP_SENSITIVITY_PROFILES
    profile = profiles.get(crop_key, profiles.get("default", {}))

    kc_map = profile.get("kc", {})
    # Try exact stage match → partial → default
    kc = kc_map.get(stage) or kc_map.get(_normalize_stage(stage)) or kc_map.get("default", 1.0)

    sensitive_stages = profile.get("sensitive_stages", [])
    is_sensitive = (
        profile.get("always_sensitive", False)
        or stage in sensitive_stages
        or _normalize_stage(stage) in sensitive_stages
        or "all" in sensitive_stages
    )

    return round(float(kc), 3), bool(is_sensitive)


def _normalize_stage(stage: str) -> str:
    """Normalise stage names: 'Fruit Development' → 'fruit_development'."""
    return stage.lower().replace(" ", "_")

"""
AI Plugin — XGBoost Decision Engine
Two models:
  1. classifier  → skip (0) | delay (1) | irrigate (2)
  2. regressor   → recommended_duration_min
Features match bio_dataset_xgb_decision_55k.json
"""
import os
import sys
import math
import joblib
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime
from backend.config.settings import get_settings
from backend.utils.logger import logger

settings = get_settings()

_classifier = None
_regressor = None

DECISION_LABELS = {0: "skip", 1: "delay", 2: "irrigate"}
FEATURE_NAMES = [
    "current_moisture", "predicted_moisture_6h", "predicted_moisture_24h",
    "target_moisture_min", "target_moisture_max", "moisture_deficit_mm",
    "day_after_planting", "rain_prob_6h", "rain_prob_24h", "last_irrigation_hours_ago",
    "temperature_c", "humidity_pct", "time_sin", "time_cos", "trust_score_avg_zone",
    "soil_encoded", "water_stress_days", "osmotic_shock_sensitive",
    "tsi", "vpd_kpa", "etc_mm_per_hour", "kc"
]


def load_xgb_models():
    global _classifier, _regressor
    clf_path = os.path.join(settings.MODELS_DIR, "xgb_classifier.pkl")
    reg_path = os.path.join(settings.MODELS_DIR, "xgb_duration.pkl")
    try:
        _classifier = joblib.load(clf_path)
        _regressor = joblib.load(reg_path)
        logger.info("[xgb] XGBoost models loaded.")
    except FileNotFoundError:
        logger.warning("[xgb] Models not found — using rule-based fallback.")


def decide_irrigation(
    current_moisture: float,
    predicted_moisture_6h: float,
    predicted_moisture_24h: float,
    target_moisture_min: float,
    target_moisture_max: float,
    days_after_planting: int,
    weather_rain_prob_6h: float,
    weather_rain_prob_24h: float,
    last_irrigation_hours_ago: float,
    temperature_avg_6h: float,
    humidity_avg_6h: float,
    trust_score_avg_zone: float,
    soil_type_encoded: int = 1,
    profile: dict = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Returns: { decision, duration_min, target_moisture, confidence, feature_importance }
    """
    now = now or datetime.utcnow()
    hour = now.hour
    time_of_day_sin = math.sin(2 * math.pi * hour / 24)
    time_of_day_cos = math.cos(2 * math.pi * hour / 24)

    # ── Stage & Bio Engine Computations ──────────────────────────────────────────
    try:
        from backend.plugins.meta.bio_engine import compute_etc, compute_tsi, compute_vpd
        from backend.plugins.ai.stage.stage_model import predict_stage
        
        if profile is None:
            raise ValueError("No profile provided to decide_irrigation")
            
        # Get refined stage data (includes moisture correction/delay)
        stage_data = predict_stage(
            crop=profile.get("name", "Maize"),
            season=profile.get("season", "kharif"),
            days_after_planting=days_after_planting,
            soil_moisture_avg_24h=current_moisture
        )
        
        kc = stage_data["kc"]
        # Update targets if the stage lookup provides more accurate ones
        target_moisture_min = stage_data.get("target_moisture_min", target_moisture_min)
        target_moisture_max = stage_data.get("target_moisture_max", target_moisture_max)

        vpd_kpa = compute_vpd(temperature_avg_6h, humidity_avg_6h)
        etc_mm_per_hour = compute_etc(temperature_avg_6h, humidity_avg_6h, kc)
        tsi = compute_tsi(temperature_avg_6h, humidity_avg_6h)
        osmotic_shock = 1 if profile.get("osmotic_shock_sensitive") else 0
    except Exception as e:
        logger.warning(f"[xgb] Stage/Bio engine computation failed: {e}. Fallback values.")
        kc, vpd_kpa, etc_mm_per_hour, tsi, osmotic_shock = 1.0, 1.0, 0.1, 40.0, 0
    
    moisture_deficit_mm = max(0.0, target_moisture_min - current_moisture)
    water_stress_days = 0 # Approximated

    features = np.array([[
        current_moisture, predicted_moisture_6h, predicted_moisture_24h,
        target_moisture_min, target_moisture_max, moisture_deficit_mm,
        days_after_planting, weather_rain_prob_6h, weather_rain_prob_24h,
        last_irrigation_hours_ago, temperature_avg_6h, humidity_avg_6h,
        time_of_day_sin, time_of_day_cos,
        trust_score_avg_zone, soil_type_encoded, water_stress_days,
        osmotic_shock, tsi, vpd_kpa, etc_mm_per_hour, kc
    ]], dtype=np.float32)

    # ── XGBoost inference ──────────────────────────────────────────────────
    if _classifier is not None and _regressor is not None:
        try:
            proba = _classifier.predict_proba(features)[0]
            decision_idx = int(np.argmax(proba))
            decision = DECISION_LABELS.get(decision_idx, "skip")
            duration = float(_regressor.predict(features)[0])
            fi = dict(zip(FEATURE_NAMES, _classifier.feature_importances_.tolist()))

            confidence = float(proba[decision_idx])
            final_confidence = min(confidence, settings.MAX_MODEL_CONFIDENCE)
            
            if trust_score_avg_zone:
                final_confidence *= float(trust_score_avg_zone)

            return {
                "decision": decision,
                "duration_min": round(duration, 1),
                "target_moisture": round((target_moisture_min + target_moisture_max) / 2, 1),
                "confidence": round(final_confidence, 4),
                "raw_confidence": round(confidence, 4),
                "feature_importance": fi,
                "method": "xgboost",
                "status": "success",
            }
        except Exception as e:
            logger.warning(f"[xgb] Inference failed: {e}")

    # ── Rule-based fallback ────────────────────────────────────────────────
    return _rule_based_decision(
        current_moisture, target_moisture_min, target_moisture_max,
        moisture_deficit_mm, weather_rain_prob_6h, last_irrigation_hours_ago,
        trust_score=trust_score_avg_zone
    )


def _rule_based_decision(
    moisture, t_min, t_max, deficit, rain_prob, last_irr_h, trust_score: float = 1.0
) -> Dict[str, Any]:
    if rain_prob > 0.6:
        return {"decision": "skip", "duration_min": 0, "target_moisture": (t_min+t_max)/2,
                "confidence": round(0.7 * trust_score, 4), "feature_importance": {}, "method": "rule", "status": "fallback"}
    if deficit > 15:
        duration = min(90, max(10, int(deficit * 1.5)))
        return {"decision": "irrigate", "duration_min": duration, "target_moisture": (t_min+t_max)/2,
                "confidence": round(0.65 * trust_score, 4), "feature_importance": {}, "method": "rule", "status": "fallback"}
    if deficit > 5:
        return {"decision": "delay", "duration_min": 0, "target_moisture": (t_min+t_max)/2,
                "confidence": round(0.6 * trust_score, 4), "feature_importance": {}, "method": "rule", "status": "fallback"}
    return {"decision": "skip", "duration_min": 0, "target_moisture": (t_min+t_max)/2,
            "confidence": round(0.75 * trust_score, 4), "feature_importance": {}, "method": "rule", "status": "fallback"}


"""
Core Reliability — Anomaly Detection (v2)
Multi-layer ensemble:
  1. Hard physics gates (instant, infallible)
  2. IsolationForest ML model (if loaded)
  3. Pattern classifiers (oscillation, cross-paradox, stuck-high)
  4. Severity scoring: low / medium / high / critical
"""
import os
import joblib
import numpy as np
from collections import deque
from typing import Optional, List, Dict, Any
from backend.utils.logger import logger
from backend.config.settings import get_settings

settings = get_settings()

# ── Anomaly taxonomy ─────────────────────────────────────────────────────────
ANOMALY_TYPES = [
    "spike_high",           # sudden jump above physical ceiling
    "spike_low",            # sudden crash below physical floor
    "sensor_stuck",         # no change over multiple readings
    "sensor_stuck_high",    # stuck at unrealistically high value
    "rapid_drop",           # exceeds soil-type max drainage rate
    "temp_anomaly",         # temperature beyond sensor operating range
    "paradox_low_moisture", # high humidity but dry soil → cable/probe issue
    "paradox_high_moisture",# low humidity but saturated soil → environment mismatch
    "oscillating_sensor",   # moisture bouncing rapidly → loose connection
    "out_of_bounds",        # raw value outside 0-100
    "missing_data",         # None reading
    "cross_validation_fail",# multiple sensors contradict each other
]

SEVERITY_MAP = {
    "out_of_bounds": "critical",
    "missing_data": "critical",
    "paradox_low_moisture": "high",
    "paradox_high_moisture": "high",
    "oscillating_sensor": "high",
    "rapid_drop": "high",
    "spike_high": "medium",
    "spike_low": "medium",
    "temp_anomaly": "medium",
    "sensor_stuck_high": "medium",
    "sensor_stuck": "low",
    "cross_validation_fail": "medium",
}

# ── Rolling window for oscillation detection (per zone, keyed by zone_id) ────
_moisture_windows: Dict[str, deque] = {}

_model = None
_scaler = None


def load_anomaly_model():
    """Load IsolationForest model + scaler from models_store/."""
    global _model, _scaler
    model_path = os.path.join(settings.MODELS_DIR, "isolation_forest.pkl")
    scaler_path = os.path.join(settings.MODELS_DIR, "anomaly_scaler.pkl")
    try:
        _model = joblib.load(model_path)
        _scaler = joblib.load(scaler_path)
        logger.info("[anomaly] IsolationForest model loaded successfully.")
    except FileNotFoundError:
        logger.warning("[anomaly] Model files not found — using rule-based ensemble fallback.")
    except Exception as e:
        logger.error(f"[anomaly] Model load error: {e}")


# ── Public entry point ────────────────────────────────────────────────────────

def detect_anomaly(
    soil_moisture: Optional[float],
    temperature: Optional[float],
    humidity: Optional[float],
    moisture_change_rate: float = 0.0,  # %/hour — computed by caller
    temp_change_rate: float = 0.0,
    z_score_moisture: float = 0.0,
    soil_type: str = "loam",
    zone_id: Optional[str] = None,      # enables oscillation tracking
    peer_moistures: Optional[List[float]] = None,  # cross-zone validation
) -> Dict[str, Any]:
    """
    Returns:
      {
        is_anomaly        : bool,
        anomaly_type      : str | None,
        anomaly_score     : float,   # 0.0 → normal, 1.0 → definite anomaly
        severity          : str,     # "low" | "medium" | "high" | "critical" | None
        confidence        : float,   # 0.0–1.0
        method            : str,
        detail            : str | None
      }
    """

    # ── Layer 1: Hard physics gates ───────────────────────────────────────────
    if soil_moisture is None:
        return _make_result("missing_data", 1.0, 1.0, "physics", "Null sensor reading")

    if soil_moisture < 0.0 or soil_moisture > 100.0:
        return _make_result("out_of_bounds", 1.0, 1.0, "physics",
                            f"Raw value {soil_moisture:.1f}% outside 0-100 range")

    # Temperature paradox (thermometer beyond operating range)
    if temperature is not None and (temperature > 65.0 or temperature < -10.0):
        return _make_result("temp_anomaly", 0.95, 0.95, "physics",
                            f"Temperature {temperature:.1f}°C beyond sensor operating range")

    # Humidity-Moisture cross paradox: wet air, bone-dry soil → disconnected probe
    if humidity is not None and humidity >= 80.0 and soil_moisture < 18.0:
        return _make_result("paradox_low_moisture", 0.92, 0.90, "physics",
                            f"Humidity={humidity:.0f}% but soil={soil_moisture:.1f}% — probe likely disconnected")

    # Inverse paradox: very low humidity but saturated soil
    if humidity is not None and humidity < 25.0 and soil_moisture > 85.0:
        return _make_result("paradox_high_moisture", 0.88, 0.85, "physics",
                            f"Humidity={humidity:.0f}% but soil={soil_moisture:.1f}% — environment mismatch")

    # Stuck at unrealistically high value (>95% for many hours)
    if soil_moisture > 95.0:
        return _make_result("sensor_stuck_high", 0.85, 0.82, "physics",
                            f"Moisture={soil_moisture:.1f}% → stuck at ceiling (waterlogging or faulty sensor)")

    # Rapid drop exceeding soil physics
    max_drop = settings.MAX_MOISTURE_DROP_PCT_PER_HOUR.get(
        soil_type, settings.MAX_MOISTURE_DROP_PCT_PER_HOUR["default"]
    )
    if moisture_change_rate < -max_drop:
        return _make_result("rapid_drop", min(0.95, abs(moisture_change_rate) / (max_drop * 2)), 0.90,
                            "physics",
                            f"Drop rate {moisture_change_rate:.2f}%/hr exceeds {soil_type} max ({max_drop:.1f}%/hr)")

    # ── Layer 2: Oscillation detection (rolling window) ──────────────────────
    if zone_id is not None:
        osc = _check_oscillation(zone_id, soil_moisture)
        if osc["is_oscillating"]:
            return _make_result("oscillating_sensor", 0.87, 0.85, "oscillation",
                                f"Moisture oscillating ±{osc['amplitude']:.1f}% in {osc['window']} readings")

    # ── Layer 3: Cross-zone validation ───────────────────────────────────────
    if peer_moistures and len(peer_moistures) >= 2:
        peer_mean = float(np.mean(peer_moistures))
        deviation = abs(soil_moisture - peer_mean)
        if deviation > settings.CORRELATION_THRESHOLD_PCT * 1.5:
            return _make_result("cross_validation_fail",
                                round(min(0.85, deviation / (settings.CORRELATION_THRESHOLD_PCT * 2)), 3),
                                0.75, "cross_zone",
                                f"Zone reading {soil_moisture:.1f}% deviates {deviation:.1f}% from peers (mean={peer_mean:.1f}%)")

    # ── Layer 4: IsolationForest ML inference ─────────────────────────────────
    if _model is not None and _scaler is not None:
        try:
            features = np.array([[
                soil_moisture,
                temperature if temperature is not None else 28.0,
                humidity if humidity is not None else 60.0,
                moisture_change_rate,
                temp_change_rate,
                z_score_moisture,
            ]], dtype=np.float32)
            scaled = _scaler.transform(features)
            prediction = _model.predict(scaled)[0]       # 1=normal, -1=anomaly
            raw_score = float(-_model.score_samples(scaled)[0])  # higher = more anomalous

            if prediction == -1:
                anomaly_type = _classify_anomaly_type(
                    soil_moisture, temperature, moisture_change_rate,
                    temp_change_rate, z_score_moisture
                )
                # Normalize score to 0-1 range
                score = round(min(1.0, max(0.0, raw_score)), 4)
                return _make_result(anomaly_type, score, 0.78, "isolation_forest",
                                    f"IsolationForest flagged — score={raw_score:.4f}")

            # Normal — still report the score for observability
            return _make_result(None, round(min(1.0, max(0.0, raw_score)), 4), None, "isolation_forest", None)

        except Exception as e:
            logger.warning(f"[anomaly] IsolationForest inference failed: {e}")

    # ── Layer 5: Rule-based fallback ──────────────────────────────────────────
    return _rule_based_detection(soil_moisture, temperature, moisture_change_rate, temp_change_rate)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_result(
    anomaly_type: Optional[str],
    anomaly_score: float,
    confidence: Optional[float],
    method: str,
    detail: Optional[str],
) -> Dict[str, Any]:
    """Build a standardised anomaly result dict."""
    is_anomaly = anomaly_type is not None
    severity = SEVERITY_MAP.get(anomaly_type) if is_anomaly else None
    return {
        "is_anomaly": is_anomaly,
        "anomaly_type": anomaly_type,
        "anomaly_score": round(float(anomaly_score), 4),
        "severity": severity,
        "confidence": round(float(confidence), 4) if confidence is not None else 0.0,
        "method": method,
        "detail": detail,
    }


def _check_oscillation(zone_id: str, moisture: float, window: int = 6) -> Dict[str, Any]:
    """
    Maintains a rolling window per zone and detects rapid back-and-forth moisture swings.
    A loose wire causes readings like: 55 → 23 → 56 → 22 → 57 → 21
    """
    if zone_id not in _moisture_windows:
        _moisture_windows[zone_id] = deque(maxlen=window)
    _moisture_windows[zone_id].append(moisture)

    buf = list(_moisture_windows[zone_id])
    if len(buf) < 4:
        return {"is_oscillating": False}

    # Check alternating direction changes
    diffs = [buf[i+1] - buf[i] for i in range(len(buf) - 1)]
    direction_changes = sum(
        1 for i in range(len(diffs) - 1) if diffs[i] * diffs[i+1] < 0
    )
    amplitude = (max(buf) - min(buf))

    # Oscillating = many direction changes AND large amplitude
    if direction_changes >= len(diffs) - 1 and amplitude > 10.0:
        return {"is_oscillating": True, "amplitude": amplitude, "window": len(buf)}
    return {"is_oscillating": False}


def _classify_anomaly_type(moisture, temperature, mc_rate, tc_rate, z_score) -> str:
    """Fine-grained anomaly type heuristics (used when IsolationForest says anomaly)."""
    if temperature and temperature > 50:
        return "temp_anomaly"
    if z_score > 3.5:
        return "spike_high"
    if z_score < -3.0:
        return "spike_low"
    if abs(mc_rate) < 0.015 and moisture > 15:
        return "sensor_stuck"
    if mc_rate < -4.0:
        return "rapid_drop"
    if moisture > 92:
        return "sensor_stuck_high"
    return "spike_high"  # default


def _rule_based_detection(moisture, temperature, mc_rate, tc_rate) -> Dict[str, Any]:
    """Pure heuristic fallback — no ML required."""
    if moisture > 97:
        return _make_result("sensor_stuck_high", 0.88, 0.70, "rule_based",
                            f"Moisture {moisture:.1f}% → stuck at ceiling")
    if moisture < 4:
        return _make_result("spike_low", 0.88, 0.70, "rule_based",
                            f"Moisture {moisture:.1f}% → below physical minimum")
    if temperature and temperature > 55:
        return _make_result("temp_anomaly", 0.85, 0.72, "rule_based",
                            f"Temperature {temperature:.1f}°C > 55°C limit")
    if abs(mc_rate) < 0.01 and moisture > 10:
        return _make_result("sensor_stuck", 0.70, 0.65, "rule_based",
                            f"Zero moisture change rate — sensor may be stuck")
    if mc_rate < -5.0:
        return _make_result("rapid_drop", 0.80, 0.70, "rule_based",
                            f"Drop rate {mc_rate:.2f}%/hr exceeds physical maximum")
    return _make_result(None, 0.05, None, "rule_based", None)

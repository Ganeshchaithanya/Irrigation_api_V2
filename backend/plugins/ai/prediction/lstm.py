"""
AI Plugin — LSTM Moisture Prediction
Predicts moisture at 1h, 6h, 24h horizons from time-series features.
"""
import os
import numpy as np
from typing import Optional, List
from backend.config.settings import get_settings
from backend.utils.logger import logger

settings = get_settings()

_model = None
_scaler = None
SEQUENCE_LENGTH = 12   # 12 readings × 4h intervals = 48h window


def load_lstm_model():
    global _model, _scaler
    try:
        import torch
        import joblib
        model_path = os.path.join(settings.MODELS_DIR, "lstm.pt")
        scaler_path = os.path.join(settings.MODELS_DIR, "lstm_scaler.pkl")

        if not os.path.exists(model_path):
            logger.warning("[lstm] lstm.pt not found — using linear fallback.")
            return

        from backend.plugins.ai.prediction.lstm_arch import MoistureLSTM
        _model = MoistureLSTM()
        _model.load_state_dict(torch.load(model_path, map_location="cpu"))
        _model.eval()
        _scaler = joblib.load(scaler_path)
        logger.info("[lstm] LSTM model loaded successfully.")
    except Exception as e:
        logger.warning(f"[lstm] Load failed: {e} — using linear fallback.")


def predict_moisture(
    recent_readings: List[dict],       # list of {soil_moisture, temperature, humidity, rain_prob, irrigated}
    current_moisture: float,
    temperature: float = 28.0,
    humidity: float = 65.0,
    rain_prob: float = 0.2,
) -> dict:
    """
    Returns: { predicted_1h, predicted_6h, predicted_24h, trend, confidence }
    """
    # ── LSTM inference ────────────────────────────────────────────────────
    if _model is not None and _scaler is not None:
        try:
            import torch
            features_list = []
            for r in recent_readings[-SEQUENCE_LENGTH:]:
                features_list.append([
                    r.get("soil_moisture", current_moisture),
                    r.get("temperature", temperature),
                    r.get("humidity", humidity),
                    r.get("rain_prob", rain_prob),
                    r.get("irrigated", 0),
                ])

            # Pad if not enough data
            while len(features_list) < SEQUENCE_LENGTH:
                features_list.insert(0, [current_moisture, temperature, humidity, rain_prob, 0])

            seq = np.array(features_list, dtype=np.float32)
            seq_scaled = _scaler.transform(seq)
            tensor = torch.tensor(seq_scaled, dtype=torch.float32).unsqueeze(0)  # (1, seq, features)

            with torch.no_grad():
                output = _model(tensor)  # (1, 3) → [1h, 6h, 24h]
                preds = output.squeeze().numpy()

            p1h = float(np.clip(preds[0], 0, 100))
            p6h = float(np.clip(preds[1], 0, 100))
            p24h = float(np.clip(preds[2], 0, 100))

            trend = _classify_trend(current_moisture, p6h)
            return {
                "predicted_1h": round(p1h, 2),
                "predicted_6h": round(p6h, 2),
                "predicted_24h": round(p24h, 2),
                "trend": trend,
                "confidence": 0.82,
                "method": "lstm",
            }
        except Exception as e:
            logger.warning(f"[lstm] Inference error: {e} — using linear fallback")

    # ── Linear trend fallback ─────────────────────────────────────────────
    return _linear_fallback(current_moisture, rain_prob)


def _classify_trend(current: float, predicted_6h: float) -> str:
    delta = predicted_6h - current
    if delta > 3:
        return "increasing"
    if delta < -3:
        return "decreasing"
    return "stable"


def _linear_fallback(current_moisture: float, rain_prob: float) -> dict:
    """Simple evapotranspiration-based linear decay estimate."""
    decay_rate = 1.5   # %/hour rough estimate
    if rain_prob > 0.6:
        decay_rate = -0.5  # moisture increasing

    p1h = max(0, min(100, current_moisture - decay_rate))
    p6h = max(0, min(100, current_moisture - decay_rate * 6))
    p24h = max(0, min(100, current_moisture - decay_rate * 24))

    return {
        "predicted_1h": round(p1h, 2),
        "predicted_6h": round(p6h, 2),
        "predicted_24h": round(p24h, 2),
        "trend": _classify_trend(current_moisture, p6h),
        "confidence": 0.45,
        "method": "linear_fallback",
    }

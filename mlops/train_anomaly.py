"""
MLOps — Train IsolationForest Anomaly Model
Trains on dataset_anomaly_detection.json (or bio anomaly data).
Saves:
  models_store/isolation_forest.pkl
  models_store/anomaly_scaler.pkl

Usage:
  python -m mlops.train_anomaly
  (or)
  python mlops/train_anomaly.py
"""
import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config.settings import get_settings
from backend.utils.logger import logger

settings = get_settings()

MODELS_DIR = settings.MODELS_DIR
DATA_DIR   = settings.DATA_DIR

# Feature columns to use — must match detect_anomaly() input order
FEATURES = [
    "soil_moisture",
    "temperature",
    "humidity",
    "moisture_change_rate",
    "temp_change_rate",
    "z_score_moisture",
]

# dataset_anomaly_detection.json label column (1=normal, -1=anomaly) or boolean
LABEL_COL = "is_anomaly"


def load_dataset() -> pd.DataFrame:
    """
    Load anomaly training dataset.
    Falls back to the legacy dataset if bio variant not found.
    """
    candidates = [
        os.path.join(DATA_DIR, "dataset_anomaly_detection.json"),
        os.path.join(DATA_DIR, "anomaly.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            logger.info(f"[anomaly‑train] Loading dataset: {path}")
            with open(path, "r") as f:
                raw = json.load(f)
            # Accept both list-of-dicts and {"samples": [...]}
            if isinstance(raw, dict):
                raw = raw.get("samples", raw.get("data", []))
            df = pd.DataFrame(raw)
            logger.info(f"[anomaly‑train] Loaded {len(df)} rows, columns: {list(df.columns)}")
            return df

    raise FileNotFoundError(
        f"No anomaly dataset found. Checked: {candidates}"
    )


def prepare_features(df: pd.DataFrame):
    """
    Normalise column names, fill missing features, return X and y arrays.
    Handles datasets with varied column naming conventions.
    """
    # Column alias map (dataset name → canonical name)
    aliases = {
        "soil_moisture_pct": "soil_moisture",
        "moisture":          "soil_moisture",
        "temperature_c":     "temperature",
        "temp":              "temperature",
        "humidity_pct":      "humidity",
        "hum":               "humidity",
        "mc_rate":           "moisture_change_rate",
        "tc_rate":           "temp_change_rate",
        "z_score":           "z_score_moisture",
        "moisture_z_score":  "z_score_moisture",
    }
    df = df.rename(columns=aliases)

    missing_features = [f for f in FEATURES if f not in df.columns]
    for feat in missing_features:
        logger.warning(f"[anomaly‑train] Feature '{feat}' missing — filling with 0.0")
        df[feat] = 0.0

    X = df[FEATURES].fillna(0.0).values.astype(np.float32)

    # Labels: bool or int (True/1 = anomaly)
    if LABEL_COL in df.columns:
        raw_labels = df[LABEL_COL]
        # Convert True/False or 1/0  →  IsolationForest convention -1/1
        y = np.where(raw_labels.astype(bool), -1, 1)
    else:
        logger.warning(f"[anomaly‑train] No '{LABEL_COL}' column — training unsupervised only.")
        y = None

    return X, y


def train():
    os.makedirs(MODELS_DIR, exist_ok=True)

    df = load_dataset()
    X, y = prepare_features(df)

    logger.info(f"[anomaly‑train] Feature matrix: {X.shape}")
    if y is not None:
        n_anomalies = int((y == -1).sum())
        contamination = max(0.01, min(0.5, n_anomalies / len(y)))
        logger.info(f"[anomaly‑train] Anomaly ratio: {n_anomalies}/{len(y)} "
                    f"→ contamination={contamination:.4f}")
    else:
        contamination = 0.05

    # ── Scale ────────────────────────────────────────────────────────────────
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ── Train IsolationForest ────────────────────────────────────────────────
    logger.info("[anomaly‑train] Training IsolationForest...")
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        max_samples="auto",
        max_features=1.0,
        bootstrap=False,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    # ── Evaluate if labels available ─────────────────────────────────────────
    if y is not None:
        preds = model.predict(X_scaled)
        logger.info("[anomaly‑train] Classification Report:")
        # Print to stdout so it's visible when run manually
        print(classification_report(y, preds, target_names=["anomaly(-1)", "normal(+1)"]))

        # Compute precision/recall for anomaly class manually for the log
        tp = int(((preds == -1) & (y == -1)).sum())
        fp = int(((preds == -1) & (y ==  1)).sum())
        fn = int(((preds ==  1) & (y == -1)).sum())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        logger.info(f"[anomaly‑train] Anomaly Precision: {precision:.3f}  Recall: {recall:.3f}")

    # ── Save artefacts ────────────────────────────────────────────────────────
    model_path  = os.path.join(MODELS_DIR, "isolation_forest.pkl")
    scaler_path = os.path.join(MODELS_DIR, "anomaly_scaler.pkl")

    joblib.dump(model,  model_path)
    joblib.dump(scaler, scaler_path)

    logger.info(f"[anomaly-train] Model saved  -> {model_path}")
    logger.info(f"[anomaly-train] Scaler saved -> {scaler_path}")
    logger.info("[anomaly-train] Done.")


if __name__ == "__main__":
    train()

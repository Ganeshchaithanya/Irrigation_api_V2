"""
MLOps — Train XGBoost Stage Awareness Classifier (v2)
Trains per-crop, per-season XGBoost multi-class classifiers on
bio_dataset_stage_awareness_77k.json (77k labelled samples) replacing
the old KMeans unsupervised approach.

Saves per-crop model bundles:
  models_store/stage_xgb_<Crop>_<season>.pkl
  Each bundle: { model, label_encoder, scaler, moisture_map }

Usage:
  python -m mlops.train_stage_xgb
  (or)
  python mlops/train_stage_xgb.py
"""
import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import xgboost as xgb

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config.settings import get_settings
from backend.utils.logger import logger

settings = get_settings()

MODELS_DIR = settings.MODELS_DIR
DATA_DIR   = settings.DATA_DIR

FEATURE_COLS = [
    "dap_normalized",
    "soil_moisture_avg_24h",
    "soil_moisture_trend",
    "temperature_avg_24h",
    "humidity_avg_24h",
    "irrigation_frequency_7d",
]
LABEL_COL  = "stage"
CROP_COL   = "crop"
SEASON_COL = "season"

# Minimum samples per group to bother training
MIN_SAMPLES = 100


def load_dataset() -> pd.DataFrame:
    """
    Try the large 77k bio dataset first, fall back to the older 6MB one.
    """
    candidates = [
        os.path.join(DATA_DIR, "bio_dataset_stage_awareness_77k.json"),
        os.path.join(DATA_DIR, "dataset_stage_awareness.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            logger.info(f"[stage-train] Loading dataset: {path}")
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                raw = raw.get("samples", raw.get("data", []))
            df = pd.DataFrame(raw)
            logger.info(f"[stage-train] Loaded {len(df):,} rows")
            return df

    raise FileNotFoundError(f"No stage dataset found. Checked: {candidates}")


def prepare_group(group: pd.DataFrame):
    """
    Prepare features and labels for one (crop, season) group.
    Returns (X_scaled, y_encoded, scaler, label_encoder, moisture_map)
    """
    # Fill missing features with 0
    for col in FEATURE_COLS:
        if col not in group.columns:
            group[col] = 0.0

    X = group[FEATURE_COLS].fillna(0.0).values.astype(np.float32)

    le = LabelEncoder()
    y = le.fit_transform(group[LABEL_COL].astype(str))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Build moisture_map: stage_name → {min, max}
    moisture_map = {}
    for stage_name in le.classes_:
        subset = group[group[LABEL_COL].astype(str) == stage_name]
        m_min = float(subset["target_moisture_min"].mean()) if "target_moisture_min" in subset else 50.0
        m_max = float(subset["target_moisture_max"].mean()) if "target_moisture_max" in subset else 70.0
        moisture_map[stage_name] = {"min": round(m_min, 1), "max": round(m_max, 1)}

    return X_scaled, y, scaler, le, moisture_map


def train_group(crop: str, season: str, group: pd.DataFrame) -> bool:
    """Train and save XGBoost classifier for one crop-season group."""
    n_classes = group[LABEL_COL].nunique()
    if n_classes < 2:
        logger.warning(f"[stage-train] Skipping {crop}/{season} - only {n_classes} class(es).")
        return False

    logger.info(f"[stage-train] Training {crop}/{season} - {len(group):,} samples, "
                f"{n_classes} stages: {sorted(group[LABEL_COL].unique())}")

    X_scaled, y, scaler, le, moisture_map = prepare_group(group)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
        tree_method="hist",   # fast on CPU
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    logger.info(f"[stage-train]   Accuracy: {acc * 100:.1f}%")
    print(f"\n=== {crop} / {season} ===")
    print(classification_report(y_test, preds, target_names=le.classes_))

    # ── Save bundle ───────────────────────────────────────────────────────────
    bundle = {
        "model":         model,
        "label_encoder": le,
        "scaler":        scaler,
        "moisture_map":  moisture_map,
        "classes":       list(le.classes_),
        "n_features":    len(FEATURE_COLS),
        "feature_names": FEATURE_COLS,
    }

    # Safe filename: replace spaces
    safe_crop   = crop.replace(" ", "_")
    safe_season = season.replace(" ", "_")
    fname  = f"stage_xgb_{safe_crop}_{safe_season}.pkl"
    fpath  = os.path.join(MODELS_DIR, fname)
    joblib.dump(bundle, fpath)
    logger.info(f"[stage-train]   Saved -> {fpath}")
    return True


def train():
    os.makedirs(MODELS_DIR, exist_ok=True)

    df = load_dataset()

    # Validate required columns
    for col in [LABEL_COL, CROP_COL, SEASON_COL]:
        if col not in df.columns:
            raise ValueError(f"Dataset missing required column: '{col}'")

    # Normalise dap if raw DAP provided (not normalised)
    if "dap_normalized" not in df.columns and "days_after_planting" in df.columns:
        max_dap = df.get("total_duration_days", pd.Series(dtype=float)).max()
        if pd.isna(max_dap) or max_dap == 0:
            # Estimate per-crop total_duration_days
            crop_max_dap = df.groupby(CROP_COL)["days_after_planting"].max()
            df["dap_normalized"] = df.apply(
                lambda r: r["days_after_planting"] / max(crop_max_dap.get(r[CROP_COL], 150), 1),
                axis=1,
            )
        else:
            df["dap_normalized"] = df["days_after_planting"] / max_dap
        df["dap_normalized"] = df["dap_normalized"].clip(0.0, 1.0)

    total_saved = 0
    groups = df.groupby([CROP_COL, SEASON_COL])
    logger.info(f"[stage-train] Found {len(groups)} crop/season groups.")

    for (crop, season), group in groups:
        if len(group) < MIN_SAMPLES:
            logger.warning(f"[stage-train] Skipping {crop}/{season} - only {len(group)} samples.")
            continue
        try:
            if train_group(crop, season, group.copy()):
                total_saved += 1
        except Exception as e:
            logger.error(f"[stage-train] Failed for {crop}/{season}: {e}")

    logger.info(f"[stage-train] Complete - {total_saved} models saved to '{MODELS_DIR}'")


if __name__ == "__main__":
    train()

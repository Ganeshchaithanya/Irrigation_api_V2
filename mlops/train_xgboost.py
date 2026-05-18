"""
MLOps — Train XGBoost AI Models
Trains the classification (Strategy) and regression (Duration) models on synthetic bio-data.
"""
import os
import json
import xgboost as xgb
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error

DATASET_PATH = "backend/data/bio_dataset_xgb_decision_55k.json"
MODELS_DIR = "backend/models"

def train():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    print(f"Loading Dataset: {DATASET_PATH}")
    with open(DATASET_PATH, 'r') as f:
        data = json.load(f)

    # Reconstruct robust schema
    features = []
    y_decision = []
    y_duration = []

    for item in data:
        # Flat schema from bio_dataset
        row = [
            item["current_moisture"],
            item["predicted_moisture_6h"],
            item["predicted_moisture_24h"],
            item["target_moisture_min"],
            item["target_moisture_max"],
            item["moisture_deficit_mm"],
            item["day_after_planting"],
            item["rain_prob_6h"],
            item["rain_prob_24h"],
            item["last_irrigation_hours_ago"],
            item["temperature_c"],
            item["humidity_pct"],
            item["time_sin"],
            item["time_cos"],
            item.get("trust_score_avg_zone", 1.0),
            item["soil_encoded"],
            item.get("water_stress_days", 0),
            item.get("osmotic_shock_sensitive", 0),
            item["tsi"],
            item["vpd_kpa"],
            item["etc_mm_per_hour"],
            item["kc"]
        ]
        
        features.append(row)
        # 0: skip, 1: irrigate/delay depending on how we map it. 
        # Actually bio_engine outputs 0 for skip. Let's just use decision_encoded.
        y_decision.append(item["decision_encoded"])
        y_duration.append(item["duration_min"])

    X = pd.DataFrame(features)
    
    print(f"Dataset Loaded: {len(X)} samples. Starting Training Pipeline...")

    # 1. Train Classifier
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X, y_decision, test_size=0.2, random_state=42)
    clf = xgb.XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', n_estimators=100, max_depth=5)
    clf.fit(X_train_c, y_train_c)
    
    preds_c = clf.predict(X_test_c)
    acc = accuracy_score(y_test_c, preds_c)
    print(f"[XGBoost] Classifier Accuracy: {acc * 100:.1f}%")

    # 2. Train Regressor (Only train duration on instances where we ACTUALLY irrigate, which is decision_encoded != 0)
    X_reg = []
    y_reg = []
    for i in range(len(y_decision)):
        if y_decision[i] != 0: # If not skip
            X_reg.append(features[i])
            y_reg.append(y_duration[i])
            
    X_reg = pd.DataFrame(X_reg)
    if len(X_reg) > 0:
        X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X_reg, y_reg, test_size=0.2, random_state=42)
        reg = xgb.XGBRegressor(n_estimators=100, max_depth=5)
        reg.fit(X_train_r, y_train_r)
        
        preds_r = reg.predict(X_test_r)
        mae = mean_absolute_error(y_test_r, preds_r)
        print(f"[XGBoost] Regressor MAE: {mae:.2f} minutes")
    else:
        print("[WARNING] Not enough irrigation data to train regressor.")
        reg = None

    # Export
    clf_path = os.path.join(MODELS_DIR, "xgb_classifier.pkl")
    reg_path = os.path.join(MODELS_DIR, "xgb_duration.pkl")
    
    joblib.dump(clf, clf_path)
    if reg:
        joblib.dump(reg, reg_path)
        
    print(f"Models successfully saved to '{MODELS_DIR}'. Inference engine activated.")

if __name__ == "__main__":
    train()


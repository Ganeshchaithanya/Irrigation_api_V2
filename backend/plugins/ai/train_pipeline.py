"""
AquaSol — ML Training Pipeline
Trains XGBoost, LSTM, and KMeans models from JSON datasets.
Saves results to models_store/
"""
import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import xgboost as xgb
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from backend.config.settings import get_settings
from backend.utils.logger import logger
from backend.plugins.ai.prediction.lstm_arch import MoistureLSTM

settings = get_settings()
os.makedirs(settings.MODELS_DIR, exist_ok=True)

def train_xgboost_decision():
    logger.info("--- Training XGBoost Decision Engine ---")
    data_path = os.path.join(settings.DATA_DIR, "dataset_xgb_decision.json")
    with open(data_path, "r") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    features = [
        "current_moisture", "predicted_moisture_6h", "predicted_moisture_24h",
        "target_moisture_min", "target_moisture_max", "moisture_deficit",
        "days_after_planting", "stage_encoded", "weather_rain_prob_6h",
        "weather_rain_prob_24h", "last_irrigation_hours_ago", "temperature_avg_6h",
        "humidity_avg_6h", "time_of_day_sin", "time_of_day_cos",
        "trust_score_avg_zone", "water_stress_index", "soil_type_encoded"
    ]
    
    X = df[features]
    y_cls = df["decision_encoded"]
    y_reg = df["recommended_duration_min"]
    
    # Classifier
    X_train, X_test, y_train, y_test = train_test_split(X, y_cls, test_size=0.2, random_state=42)
    clf = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    clf.fit(X_train, y_train)
    score_cls = clf.score(X_test, y_test)
    logger.info(f"Classifier accuracy: {score_cls:.4f}")
    
    # Regressor (only on irrigate samples)
    irr_mask = (df["decision"] == "irrigate")
    X_irr = X[irr_mask]
    y_irr = y_reg[irr_mask]
    
    if len(X_irr) > 0:
        X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X_irr, y_irr, test_size=0.2, random_state=42)
        reg = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
        reg.fit(X_train_r, y_train_r)
        logger.info("Regressor trained.")
    else:
        logger.warning("No 'irrigate' samples for regressor training!")
        reg = None

    # Save
    joblib.dump(clf, os.path.join(settings.MODELS_DIR, "xgb_classifier.pkl"))
    if reg:
        joblib.dump(reg, os.path.join(settings.MODELS_DIR, "xgb_duration.pkl"))
    logger.info("XGBoost models saved.")

def train_lstm_moisture():
    logger.info("--- Training LSTM Moisture Predictor ---")
    data_path = os.path.join(settings.DATA_DIR, "dataset_lstm_training.json")
    with open(data_path, "r") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    features = ["soil_moisture", "temperature", "humidity", "rain_prob", "irrigated"]
    targets = ["moisture_1h_later", "moisture_6h_later", "moisture_24h_later"]
    
    X_raw = df[features].values
    y_raw = df[targets].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    
    # Create sequences
    seq_len = 12
    X_seq, y_seq = [], []
    for i in range(len(X_scaled) - seq_len):
        X_seq.append(X_scaled[i : i + seq_len])
        y_seq.append(y_raw[i + seq_len - 1]) # Target is the label at the end of the sequence
    
    X_seq = np.array(X_seq, dtype=np.float32)
    y_seq = np.array(y_seq, dtype=np.float32)
    
    # Tensors
    X_train, X_test, y_train, y_test = train_test_split(X_seq, y_seq, test_size=0.1, random_state=42)
    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
    
    model = MoistureLSTM()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    epochs = 10
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for bx, by in train_loader:
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch+1) % 2 == 0:
            logger.info(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(train_loader):.4f}")
    
    # Save
    torch.save(model.state_dict(), os.path.join(settings.MODELS_DIR, "lstm.pt"))
    joblib.dump(scaler, os.path.join(settings.MODELS_DIR, "lstm_scaler.pkl"))
    logger.info("LSTM model saved.")

def train_kmeans_stages():
    logger.info("--- Training KMeans Stage Awareness ---")
    data_path = os.path.join(settings.DATA_DIR, "dataset_stage_awareness.json")
    with open(data_path, "r") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    features = [
        "dap_normalized", "soil_moisture_avg_24h", "soil_moisture_trend",
        "temperature_avg_24h", "humidity_avg_24h", "irrigation_frequency_7d"
    ]
    
    # Group by crop and season
    groups = df.groupby(["crop", "season"])
    for (crop, season), group in groups:
        if len(group) < 5: continue
        
        X = group[features].values.astype(np.float32)
        # Detect number of distinct stages in dataset
        n_clusters = group["stage"].nunique()
        
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        kmeans.fit(X)
        
        # Map clusters to stage names
        labels = kmeans.labels_
        label_map = {}
        moisture_map = {}
        for i in range(n_clusters):
            # Find the most frequent stage name for this cluster
            stage_names = group.iloc[labels == i]["stage"]
            if len(stage_names) == 0: continue
            stage_name = stage_names.mode()[0]
            label_map[i] = stage_name
            
            # Record average moisture requirements if available
            subset = group[group["stage"] == stage_name]
            moisture_map[stage_name] = {
                "min": float(subset["target_moisture_min"].mean()) if "target_moisture_min" in subset else 50,
                "max": float(subset["target_moisture_max"].mean()) if "target_moisture_max" in subset else 70
            }
            
        model_data = {
            "model": kmeans,
            "label_map": label_map,
            "moisture_map": moisture_map
        }
        
        fname = f"stage_kmeans_{crop}_{season}.pkl"
        joblib.dump(model_data, os.path.join(settings.MODELS_DIR, fname))
        logger.info(f"KMeans model saved for {crop}_{season}")

if __name__ == "__main__":
    try:
        train_xgboost_decision()
        train_lstm_moisture()
        train_kmeans_stages()
        logger.info("SUCCESS: All models trained and serialized.")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")

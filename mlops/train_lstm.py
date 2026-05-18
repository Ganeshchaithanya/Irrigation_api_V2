"""
MLOps — Train PyTorch LSTM Model
Trains the time-series forecasting model (MoistureLSTM) on the new bio dataset.
"""
import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.plugins.ai.prediction.lstm_arch import MoistureLSTM

DATASET_PATH = "backend/data/bio_dataset_lstm_55k.json"
MODELS_DIR = "backend/models"
EPOCHS = 15 # Reduced for local training speed
BATCH_SIZE = 32

def train():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    with open(DATASET_PATH, 'r') as f:
        data = json.load(f)

    X_raw = []
    y_raw = []

    # Use sliding window over zones
    df = pd.DataFrame(data)
    
    # Check if we literally have sequences or flat structures
    if "sequence" in data[0]:
        for item in data:
            seq = []
            for step in item["sequence"]:
                seq.append([step["soil_moisture"], step["temperature"], step["humidity"], step["rain_prob"], step["irrigated"]])
            X_raw.append(seq)
            y_raw.append([item["target_1h"], item["target_6h"], item["target_24h"]])
    else:
        # Group by zone_id, assuming ordered
        for zone_id, group in df.groupby('zone_id'):
            records = group.to_dict('records')
            for i in range(len(records) - 12):
                seq = []
                for step in records[i:i+12]:
                    seq.append([
                        step["soil_moisture_pct"],
                        step["temperature_c"],
                        step["humidity_pct"],
                        step["rain_prob"],
                        step["irrigated"]
                    ])
                last_step = records[i+11]
                X_raw.append(seq)
                y_raw.append([
                    last_step["target_moisture_1h"], 
                    last_step["target_moisture_4h"], 
                    last_step["target_moisture_24h"]
                ])

    import numpy as np
    X_np = np.array(X_raw, dtype=np.float32) # Shape: (samples, seq_len, 5)
    y_np = np.array(y_raw, dtype=np.float32) # Shape: (samples, 3)

    # Scale the features
    samples, seq_len, features = X_np.shape
    X_np_flat = X_np.reshape(-1, features)
    
    scaler = StandardScaler()
    X_np_scaled_flat = scaler.fit_transform(X_np_flat)
    X_np_scaled = X_np_scaled_flat.reshape(samples, seq_len, features)

    X_tensor = torch.tensor(X_np_scaled)
    y_tensor = torch.tensor(y_np)

    dataset = TensorDataset(X_tensor, y_tensor)
    
    # 80/20 train/val split
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

    print(f"Dataset Loaded: {samples} sequences. Starting LSTM Training Pipeline...")

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    model = MoistureLSTM(input_size=5, hidden_size=128, num_layers=2, output_size=3).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # Training Loop
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * batch_x.size(0)
            
        train_loss /= train_size
        
        # Eval
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item() * batch_x.size(0)
        val_loss /= val_size
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch [{epoch+1}/{EPOCHS}] | Train Loss: {train_loss:.2f} | Val Loss: {val_loss:.2f}")

    # Export
    model_path = os.path.join(MODELS_DIR, "lstm.pt")
    scaler_path = os.path.join(MODELS_DIR, "lstm_scaler.pkl")
    
    # Save weights and scaler
    torch.save(model.state_dict(), model_path)
    joblib.dump(scaler, scaler_path)
        
    print(f"[LSTM] PyTorch Model successfully saved to '{MODELS_DIR}'. Inference engine activated.")

if __name__ == "__main__":
    train()


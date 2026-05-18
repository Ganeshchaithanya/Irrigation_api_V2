"""
MLOps — Dataset Generator
Generates synthetic data for LSTM and XGBoost models incorporating physical traps.
"""
import json
import math
import random
import os
import sys

# Add project root to sys.path to allow importing backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.plugins.ai.stage.stage_model import predict_stage, load_stage_models
from backend.utils.logger import logger

# Disable logging for cleaner dataset generation
logger.setLevel("WARNING")

LSTM_OUTPUT = "dataset_lstm.json"
XGB_OUTPUT = "dataset_xgb.json"

def generate_lstm_data(num_samples=2000):
    dataset = []
    # 12 sequence steps (48h at 4h intervals)
    for _ in range(num_samples):
        # Scenario generation
        temp_base = random.uniform(20.0, 40.0)
        start_moisture = random.uniform(30.0, 80.0)
        is_rain = random.random() < 0.1
        
        sequence = []
        moisture = start_moisture
        for i in range(12):
            hour = (i * 4) % 24
            temp = temp_base + 5.0 * math.sin(math.pi * (hour - 6) / 12)
            humid = max(30.0, 100.0 - temp)
            
            # Simple drying physics
            evap = (temp / 30.0) * 1.5
            moisture = max(10.0, moisture - evap)
            
            rain_prob = 0.8 if (is_rain and i == 6) else random.uniform(0, 0.2)
            if rain_prob > 0.5:
                moisture = min(100.0, moisture + random.uniform(10, 30))
                
            sequence.append({
                "soil_moisture": float(round(moisture, 2)),
                "temperature": float(round(temp, 2)),
                "humidity": float(round(humid, 2)),
                "rain_prob": float(round(rain_prob, 2)),
                "irrigated": 0.0
            })
        
        # Targets are moisture at step 13 (T+1), step 14 (T+6h approx 1.5 steps, let's say step 14), step 18 (T+24h)
        # We simplify target generation:
        target_1h = max(10.0, sequence[-1]["soil_moisture"] - 0.5)
        target_6h = max(10.0, sequence[-1]["soil_moisture"] - 2.5)
        target_24h = max(10.0, sequence[-1]["soil_moisture"] - 8.0)
        
        dataset.append({
            "sequence": sequence,
            "target_1h": target_1h,
            "target_6h": target_6h,
            "target_24h": target_24h
        })
        
    with open(LSTM_OUTPUT, "w") as f:
        json.dump(dataset, f)
    print(f"LSTM Dataset generated: {LSTM_OUTPUT}")


def generate_xgb_data(num_samples=10000):
    dataset = []
    load_stage_models() # Load JSONs
    
    crops = ["Rice", "Maize", "Tomato", "Cotton"]

    for _ in range(num_samples):
        crop = random.choice(crops)
        season = "kharif"
        dap = random.randint(5, 120)
        cm = random.uniform(20, 90)
        
        # Get ground truth from our new engine
        stage_data = predict_stage(crop, season, dap, cm)
        
        t_min = stage_data["target_moisture_min"]
        t_max = stage_data["target_moisture_max"]
        
        # Expert features
        soil_type = random.choice([0, 1, 2]) # 0:Sand, 1:Loam, 2:Clay
        d_mismatch = 1 if (random.random() < 0.1) else 0
        estimated_root = cm * (0.65 if soil_type == 2 else 0.8) if d_mismatch else cm
        crop_sens_flag = 1 if stage_data["stage_sensitivity"] else 0
        
        temp = random.uniform(20, 40)
        rain_prob = random.uniform(0, 1)
        trust = random.uniform(0.3, 1.0)
        
        # The logic block
        decision = 0 # skip
        duration = 0
        
        if trust < 0.5:
            decision = 1 # delay
        elif rain_prob > 0.6:
            decision = 0 # skip
        else:
            if d_mismatch and cm > t_min and estimated_root < t_min:
                decision = 2 # irrigate (partial override)
                duration = 30
            elif estimated_root < t_min:
                decision = 2 # irrigate
                duration = min(120, int((t_min - estimated_root) * 3.5))
        
        # Add to Dataset array
        sample = {
            "current_moisture": cm,
            "predicted_moisture_6h": max(10.0, cm - 3.0),
            "predicted_moisture_24h": max(10.0, cm - 10.0),
            "target_moisture_min": t_min,
            "target_moisture_max": t_max,
            "moisture_deficit": max(0, t_min - estimated_root),
            "days_after_planting": dap,
            "effective_dap": stage_data["effective_dap"],
            "crop_stage": stage_data["stage"],
            "weather_rain_prob_6h": rain_prob,
            "weather_rain_prob_24h": rain_prob * 0.8,
            "last_irrigation_hours_ago": random.uniform(1, 100),
            "temperature_avg_6h": temp,
            "humidity_avg_6h": max(30, 100 - temp),
            "time_of_day_sin": math.sin(random.uniform(0, 2*math.pi)),
            "time_of_day_cos": math.cos(random.uniform(0, 2*math.pi)),
            "trust_score_avg_zone": trust,
            "water_stress_index": max(0, t_min - estimated_root),
            "soil_type_encoded": soil_type,
            "estimated_root_moisture": estimated_root,
            "depth_mismatch": d_mismatch,
            "is_anomaly": 1 if (trust < 0.6 and random.random() > 0.7) else 0,
            "slow_drift": 1 if (trust < 0.8 and random.random() > 0.5) else 0,
            "crop_sensitivity_flag": crop_sens_flag,
            "kc": stage_data["kc"]
        }
        
        target = {
            "decision": decision,
            "duration_min": duration
        }
        
        dataset.append({"features": sample, "targets": target})
        
    with open(XGB_OUTPUT, "w") as f:
        json.dump(dataset, f)
    print(f"XGBoost Dataset generated: {XGB_OUTPUT}")


if __name__ == "__main__":
    print("Generating Synthetic MLOps Datasets...")
    generate_lstm_data()
    generate_xgb_data()
    print("Generation Complete.")

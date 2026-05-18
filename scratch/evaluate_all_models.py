"""
Final report printer — reads the CSV and prints a clean table
"""
import pandas as pd, os, sys

out_csv = "scratch/model_evaluation_report.csv"

# ── Re-run the evaluation inline so CSV is always fresh ──────────────────────
import warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath("."))

import numpy as np
import json
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, mean_absolute_error, mean_squared_error, r2_score,
    f1_score, precision_score, recall_score
)

MODELS_DIR = "backend/models_store"
DATA_DIR   = "backend/data"

rows = []

def rmse_fn(a, b): return float(np.sqrt(mean_squared_error(a, b)))

XGB_FEATURES = [
    "current_moisture","predicted_moisture_6h","predicted_moisture_24h",
    "target_moisture_min","target_moisture_max","moisture_deficit",
    "days_after_planting","stage_encoded","weather_rain_prob_6h",
    "weather_rain_prob_24h","last_irrigation_hours_ago","temperature_avg_6h",
    "humidity_avg_6h","time_of_day_sin","time_of_day_cos",
    "trust_score_avg_zone","water_stress_index","soil_type_encoded",
]
XGB_ALIAS = {
    "day_after_planting":"days_after_planting","rain_prob_6h":"weather_rain_prob_6h",
    "rain_prob_24h":"weather_rain_prob_24h","temperature_c":"temperature_avg_6h",
    "humidity_pct":"humidity_avg_6h","time_sin":"time_of_day_sin",
    "time_cos":"time_of_day_cos","water_stress_days":"water_stress_index",
    "soil_encoded":"soil_type_encoded","moisture_deficit_mm":"moisture_deficit",
}

def load_xgb():
    path = os.path.join(DATA_DIR,"bio_dataset_xgb_decision_55k.json")
    with open(path) as f: data = json.load(f)
    df = pd.DataFrame(data).rename(columns=XGB_ALIAS)
    for feat in XGB_FEATURES:
        if feat not in df.columns: df[feat]=0.0
    return df

# 1. XGB Classifier
df_xgb = load_xgb()
X,y = df_xgb[XGB_FEATURES], df_xgb["decision_encoded"]
_,Xt,_,yt = train_test_split(X,y,test_size=0.2,random_state=42)
clf = joblib.load(os.path.join(MODELS_DIR,"xgb_classifier.pkl"))
p = clf.predict(Xt)
rows.append({"Model":"XGBoost Classifier","Task":"Irrigation Decision (3-class)",
 "Accuracy":f"{accuracy_score(yt,p)*100:.2f}%","F1":f"{f1_score(yt,p,average='weighted'):.4f}",
 "Precision":f"{precision_score(yt,p,average='weighted',zero_division=0):.4f}",
 "Recall":f"{recall_score(yt,p,average='weighted',zero_division=0):.4f}",
 "MAE":"—","RMSE":"—","R2":"—","N_test":len(yt)})

# 2. XGB Regressor
df_irr = df_xgb[df_xgb["decision_encoded"]!=0]
X2,y2 = df_irr[XGB_FEATURES], df_irr["duration_min"]
_,Xt2,_,yt2 = train_test_split(X2,y2,test_size=0.2,random_state=42)
reg = joblib.load(os.path.join(MODELS_DIR,"xgb_duration.pkl"))
p2 = reg.predict(Xt2)
rows.append({"Model":"XGBoost Regressor","Task":"Irrigation Duration (min)",
 "Accuracy":"—","F1":"—","Precision":"—","Recall":"—",
 "MAE":f"{mean_absolute_error(yt2,p2):.2f} min",
 "RMSE":f"{rmse_fn(yt2,p2):.2f} min","R2":f"{r2_score(yt2,p2):.4f}","N_test":len(yt2)})

# 3. LSTM
try:
    import torch
    from backend.plugins.ai.prediction.lstm_arch import MoistureLSTM
    path = os.path.join(DATA_DIR,"bio_dataset_lstm_55k.json")
    with open(path) as f: data3=json.load(f)
    X3_raw,y3_raw=[],[]
    if "sequence" in data3[0]:
        for item in data3:
            X3_raw.append([[s["soil_moisture"],s["temperature"],s["humidity"],s["rain_prob"],s["irrigated"]] for s in item["sequence"]])
            y3_raw.append([item["target_1h"],item["target_6h"],item["target_24h"]])
    else:
        df3=pd.DataFrame(data3)
        for _,grp in df3.groupby("zone_id"):
            recs=grp.to_dict("records")
            for i in range(len(recs)-12):
                X3_raw.append([[r["soil_moisture_pct"],r["temperature_c"],r["humidity_pct"],r["rain_prob"],r["irrigated"]] for r in recs[i:i+12]])
                last=recs[i+11]
                y3_raw.append([last["target_moisture_1h"],last["target_moisture_4h"],last["target_moisture_24h"]])
    X3=np.array(X3_raw,dtype=np.float32); y3=np.array(y3_raw,dtype=np.float32)
    s3,sl3,f3=X3.shape
    sc3=joblib.load(os.path.join(MODELS_DIR,"lstm_scaler.pkl"))
    X3s=sc3.transform(X3.reshape(-1,f3)).reshape(s3,sl3,f3)
    sp=int(0.8*s3); Xt3=X3s[sp:]; yt3=y3[sp:]
    m3=MoistureLSTM(5,128,2,3); m3.load_state_dict(torch.load(os.path.join(MODELS_DIR,"lstm.pt"),map_location="cpu")); m3.eval()
    with torch.no_grad(): p3=m3(torch.tensor(Xt3)).numpy()
    for i,lbl in enumerate(["1h","6h","24h"]):
        rows.append({"Model":f"LSTM ({lbl} forecast)","Task":f"Soil Moisture ({lbl})",
         "Accuracy":"—","F1":"—","Precision":"—","Recall":"—",
         "MAE":f"{mean_absolute_error(yt3[:,i],p3[:,i]):.4f}",
         "RMSE":f"{rmse_fn(yt3[:,i],p3[:,i]):.4f}","R2":f"{r2_score(yt3[:,i],p3[:,i]):.4f}","N_test":len(yt3)})
except Exception as e:
    for lbl in ["1h","6h","24h"]:
        rows.append({"Model":f"LSTM ({lbl} forecast)","Task":f"Soil Moisture ({lbl})",
         "Accuracy":"—","F1":"—","Precision":"—","Recall":"—","MAE":"N/A","RMSE":"N/A","R2":"N/A","N_test":"N/A"})
    print(f"LSTM SKIP: {e}")

# 4. Isolation Forest
FEATS4=["soil_moisture","temperature","humidity","moisture_change_rate","temp_change_rate","z_score_moisture"]
ALIAS4={"soil_moisture_pct":"soil_moisture","moisture":"soil_moisture","temperature_c":"temperature",
        "humidity_pct":"humidity","mc_rate":"moisture_change_rate","tc_rate":"temp_change_rate",
        "z_score":"z_score_moisture","moisture_z_score":"z_score_moisture"}
with open(os.path.join(DATA_DIR,"dataset_anomaly_detection.json")) as f: raw4=json.load(f)
if isinstance(raw4,dict): raw4=raw4.get("samples",raw4.get("data",[]))
df4=pd.DataFrame(raw4).rename(columns=ALIAS4)
for feat in FEATS4:
    if feat not in df4.columns: df4[feat]=0.0
X4=df4[FEATS4].fillna(0.0).values.astype(np.float32)
y4=np.where(df4["is_anomaly"].astype(bool),-1,1) if "is_anomaly" in df4.columns else None
sc4=joblib.load(os.path.join(MODELS_DIR,"anomaly_scaler.pkl"))
m4=joblib.load(os.path.join(MODELS_DIR,"isolation_forest.pkl"))
p4=m4.predict(sc4.transform(X4))
if y4 is not None:
    tp=int(((p4==-1)&(y4==-1)).sum()); fp=int(((p4==-1)&(y4==1)).sum()); fn=int(((p4==1)&(y4==-1)).sum())
    ap=tp/(tp+fp) if (tp+fp)>0 else 0; ar=tp/(tp+fn) if (tp+fn)>0 else 0
    rows.append({"Model":"Isolation Forest","Task":"Sensor Anomaly Detection",
     "Accuracy":f"{accuracy_score(y4,p4)*100:.2f}%","F1":f"{f1_score(y4,p4,average='weighted'):.4f}",
     "Precision":f"{ap:.4f} (anom)","Recall":f"{ar:.4f} (anom)",
     "MAE":"—","RMSE":"—","R2":"—","N_test":len(y4)})

# 5. Stage XGB
FEAT5=["dap_normalized","soil_moisture_avg_24h","soil_moisture_trend","temperature_avg_24h","humidity_avg_24h","irrigation_frequency_7d"]
with open(os.path.join(DATA_DIR,"bio_dataset_stage_awareness_77k.json"),encoding="utf-8") as f: raw5=json.load(f)
if isinstance(raw5,dict): raw5=raw5.get("samples",raw5.get("data",[]))
df5=pd.DataFrame(raw5)
if "dap_normalized" not in df5.columns and "days_after_planting" in df5.columns:
    cm=df5.groupby("crop")["days_after_planting"].max()
    df5["dap_normalized"]=df5.apply(lambda r:r["days_after_planting"]/max(cm.get(r["crop"],150),1),axis=1).clip(0,1)

bundles=[f for f in os.listdir(MODELS_DIR) if f.startswith("stage_xgb_")]
accs5,f1s5=[],[]
for bfile in sorted(bundles):
    bun=joblib.load(os.path.join(MODELS_DIR,bfile))
    tag=bfile.replace("stage_xgb_","").replace(".pkl","")
    li=tag.rfind("_"); cr=tag[:li].replace("_"," "); se=tag[li+1:].replace("_"," ")
    sub=df5[(df5["crop"]==cr)&(df5["season"]==se)].copy()
    if len(sub)<50: continue
    for c in FEAT5:
        if c not in sub.columns: sub[c]=0.0
    le=bun["label_encoder"]; vm=sub["stage"].astype(str).isin(le.classes_); sub=sub[vm]
    if len(sub)==0: continue
    X5=sub[FEAT5].fillna(0.0).values.astype(np.float32)
    y5=le.transform(sub["stage"].astype(str))
    X5s=bun["scaler"].transform(X5)
    _,Xt5,_,yt5=train_test_split(X5s,y5,test_size=0.2,random_state=42,stratify=y5)
    p5=bun["model"].predict(Xt5)
    acc5=accuracy_score(yt5,p5); f15=f1_score(yt5,p5,average="weighted",zero_division=0)
    prec5=precision_score(yt5,p5,average="weighted",zero_division=0)
    rec5=recall_score(yt5,p5,average="weighted",zero_division=0)
    accs5.append(acc5); f1s5.append(f15)
    rows.append({"Model":f"Stage-XGB  {cr} ({se})","Task":f"Crop Stage ({len(le.classes_)} classes)",
     "Accuracy":f"{acc5*100:.2f}%","F1":f"{f15:.4f}","Precision":f"{prec5:.4f}","Recall":f"{rec5:.4f}",
     "MAE":"--","RMSE":"--","R2":"--","N_test":len(yt5)})

if accs5:
    rows.append({"Model":"[AGGREGATE] Stage-XGB (mean)","Task":"All Crops / All Seasons",
     "Accuracy":f"{np.mean(accs5)*100:.2f}%","F1":f"{np.mean(f1s5):.4f}",
     "Precision":"(see rows)","Recall":"(see rows)","MAE":"--","RMSE":"--","R2":"--","N_test":"--"})

# ── Final Table ──────────────────────────────────────────────────────────────
df_out = pd.DataFrame(rows).rename(columns={"R2":"R^2","N_test":"N(test)"})
COLS=["Model","Task","Accuracy","F1","Precision","Recall","MAE","RMSE","R^2","N(test)"]
df_out = df_out[COLS]
df_out.to_csv(out_csv, index=False, encoding="utf-8")

sep="="*150
print(sep)
print("  AQUASOL AI ENGINE  --  FULL MODEL EVALUATION REPORT")
print(sep)
pd.set_option("display.max_colwidth",55)
pd.set_option("display.width",300)
pd.set_option("display.max_rows",100)
sys.stdout.reconfigure(encoding="utf-8")
print(df_out.to_string(index=False))
print(sep)
print(f"[OK] CSV saved -> {out_csv}")

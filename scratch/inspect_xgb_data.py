import json
with open("backend/data/bio_dataset_xgb_decision_55k.json") as f:
    d = json.load(f)
print("Keys in first record:", list(d[0].keys()))
print("\nTotal records:", len(d))

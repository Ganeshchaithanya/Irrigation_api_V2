import os, joblib

MODELS_DIR = "backend/models_store"

clf = joblib.load(os.path.join(MODELS_DIR, "xgb_classifier.pkl"))
print("=== XGB Classifier feature names ===")
print(clf.get_booster().feature_names)

reg = joblib.load(os.path.join(MODELS_DIR, "xgb_duration.pkl"))
print("\n=== XGB Regressor feature names ===")
print(reg.get_booster().feature_names)

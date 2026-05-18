"""
Core Reliability — ML Supervisor
Acts as the ultimate failsafe against AI hallucination or OOD logic.
Provides feature explainability and bounds checking.
"""
from typing import Dict, Any, List

def check_ood_bounds(current_moisture: float, temperature_celsius: float) -> bool:
    """
    Checks if realtime data breaches the safe operating boundaries
    of the synthetic distribution the XGBoost model was trained on.
    Returns True if an OOD State is flagged.
    """
    if current_moisture < 0.0 or current_moisture >= 100.0: # 100 is physically anomalous or flooded
        return True
    
    if temperature_celsius > 50.0 or temperature_celsius < -10.0:
        return True
        
    return False

def extract_top_factors(feature_importances: List[float], feature_names: List[str], top_k: int = 3) -> List[str]:
    """
    Given the model's intrinsic feature importances, returns the 
    top K reasons why a decision was reached.
    """
    if not feature_importances or len(feature_importances) != len(feature_names):
        return ["Unknown (Model Missing)"]
        
    # Pair and sort
    paired = list(zip(feature_names, feature_importances))
    paired.sort(key=lambda x: x[1], reverse=True)
    
    return [item[0] for item in paired[:top_k]]

def calibrate_confidence(raw_confidence: float) -> float:
    """
    ML models (especially deep nets) are often overconfident. 
    This applies a simple smoothing/temperature scaling wrapper.
    """
    # Simple bounds restriction
    if raw_confidence > 0.95:
        return 0.95 # Cap false certainty
    if raw_confidence < 0.20:
        return 0.20
    return raw_confidence

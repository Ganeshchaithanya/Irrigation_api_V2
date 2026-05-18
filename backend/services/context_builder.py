"""
Service — Context Builder (v2)
Assembles real-time system state into a structured LLM context object.
Enriched with v2 model insights (Anomaly Severity, Stage Progress, Sensitivity).
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.core.state.state_manager import state_manager


async def build_chat_context(
    farm_id: str,
    farm_name: str,
    zone_ids: List[str],
    weather: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Build the full context dict injected into the chatbot system prompt.
    Reads from in-memory state cache — no DB hit needed.
    """
    zones_context = []
    for zid in zone_ids:
        state = state_manager.get_cached_zone_context(zid)
        if not state:
            continue
            
        # Extract v2 insights
        uncertainty = state.get("uncertainty_flag")
        # Map uncertainty to severity if possible
        severity = "Normal"
        if uncertainty:
            # We assume the anomaly engine or state manager has tagged severity
            # If not, we just pass the flag itself
            severity = state.get("anomaly_severity") or "Alert: " + str(uncertainty)

        zones_context.append({
            "zone_id": zid,
            "crop": state.get("current_stage"),  # Fallback to current_stage if crop name missing
            "moisture_now": state.get("current_moisture"),
            "moisture_target": f"{state.get('target_moisture_min')}-{state.get('target_moisture_max')}%",
            "predicted_6h": state.get("predicted_moisture_6h"),
            "predicted_24h": state.get("predicted_moisture_24h"),
            
            # v2 Stage Model Outputs
            "stage": state.get("current_stage"),
            "growth_progress": f"{state.get('growth_progress_pct', 0)}%",
            "stage_sensitive": state.get("stage_sensitivity", False),
            "kc": state.get("kc"),
            
            "valve_state": "OPEN" if str(state.get("valve_state")).lower() == "open" else "CLOSED",
            "last_irrigation": str(state.get("last_irrigation_at", "N/A")),
            "last_irrigation_duration": state.get("last_irrigation_duration"),
            
            # Perception & Reliability
            "trust_score": round(float(state.get("trust_score_avg") or 1.0), 2),
            "status": severity,
            "rolling_avg_24h": state.get("rolling_avg_24h"),
            "active_plan_task": state.get("active_plan_task"),
            "alerts": state.get("active_alerts", []),
        })

    last_decision = None
    if zones_context:
        # Get the most recent decision from the first zone as a summary
        first_zid = zone_ids[0]
        first_state = state_manager.get_cached_zone_context(first_zid)
        if first_state:
            last_decision = {
                "action": first_state.get("ai_recommendation") or first_state.get("last_decision"),
                "at": str(first_state.get("updated_at") or first_state.get("last_decision_at")),
                "confidence": first_state.get("model_confidence"),
            }

    return {
        "farm_name": farm_name,
        "zones": zones_context,
        "active_alerts": [a for z in zones_context for a in z.get("alerts", [])],
        "weather": weather or {},
        "last_decision": last_decision,
        "system_timestamp": datetime.now(timezone.utc).isoformat(),
    }

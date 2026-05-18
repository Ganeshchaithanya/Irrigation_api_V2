"""
Control — Execution Controller
Orchestrates: Final Decision → Policy Gate → MQTT Publish → DB Log
This is the ONLY component that sends hardware commands.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import json

from backend.control.command_builder import build_irrigate_command, build_stop_command
from backend.models.decision import DecisionLog, ValveCommand
from backend.models.state import ZoneState
from backend.core.state.state_manager import state_manager
from backend.utils.logger import logger
from backend.services.diary_builder import diary_builder


async def execute_decision(
    zone_id: str,
    farm_id: str,
    final_decision: Dict[str, Any],
    db: AsyncSession,
    master_mac: str = "",
    node_slot_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Takes a validated final decision dict and executes it:
    1. Save DecisionLog to DB
    2. If irrigate → publish MQTT + save ValveCommand
    3. Update ZoneState
    4. Return execution result
    """
    action = final_decision.get("decision", "skip")
    duration_min = final_decision.get("duration_min", 0)
    confidence = final_decision.get("confidence")
    is_manual = final_decision.get("is_manual_override", False)

    feature_snapshot = {
        "current_moisture": final_decision.get("current_moisture"),
        "predicted_6h": final_decision.get("predicted_6h"),
        "predicted_24h": final_decision.get("predicted_24h"),
        "rain_prob_6h": final_decision.get("rain_prob_6h"),
        "target_moisture": final_decision.get("target_moisture"),
        "stage": final_decision.get("stage"),
        "feature_importance": final_decision.get("feature_importance"),
    }

    # ── Step 1: Persist Decision ─────────────────────────────────────────
    # Join structured reasoning into a single bulleted string
    reasons = final_decision.get("policy_reason")
    if isinstance(reasons, list):
        explanation_str = " | ".join(reasons)
    else:
        explanation_str = str(reasons) if reasons else "AI Intelligence Inference"

    import uuid
    decision_record = DecisionLog(
        zone_id=uuid.UUID(str(zone_id)) if zone_id else None,
        decision=action,
        duration_min=final_decision.get("duration_per_cycle_min", duration_min),
        water_required_mm=final_decision.get("water_required_mm"),
        cycles=final_decision.get("cycles", 1),
        confidence=final_decision.get("confidence"),
        policy_blocked=final_decision.get("policy_applied") is not None,
        block_reason=final_decision.get("policy_applied"),
        feature_snapshot=feature_snapshot,
        top_factors=final_decision.get("top_factors"),
        ood_flag=final_decision.get("ood_flag", False),
        explanation=explanation_str
    )
    db.add(decision_record)
    await db.flush()
    logger.info(f"[controller] Decision saved id={decision_record.id} action={action} zone={zone_id}")

    # ── Step 2: MQTT Publish & ValveCommand ──────────────────────────────
    mqtt_sent = False
    operating_mode = final_decision.get("operating_mode", "active")
    action_now = final_decision.get("action_now", "SKIP")
    
    if action in ("irrigate", "irrigate_partial") or action_now == "IRRIGATE":
        # For precision mode, we send duration_per_cycle_min
        dur_per_cycle = final_decision.get("duration_per_cycle_min", duration_min)
        num_cycles = final_decision.get("cycles", 1)
        soak_min = final_decision.get("soak_time_min", 0)

        payload = build_irrigate_command(
            zone_id, 
            dur_per_cycle, 
            final_decision.get("target_moisture", 65.0), 
            decision_record.id,
            cycles=num_cycles,
            soak_time_min=soak_min
        )
        # Check Shadow Mode
        if operating_mode == "shadow":
            logger.info(f"[controller] SHADOW MODE ACTIVE: Bypassing hardware actuation for Zone {zone_id}.")
        else:
            # Note: We no longer publish via MQTT. The command is queued in DB for HTTP polling.
            pass

        import uuid
        cmd = ValveCommand(
            id=uuid.uuid4(),
            zone_id=uuid.UUID(str(zone_id)) if zone_id else None,
            node_slot_id=uuid.UUID(str(node_slot_id)) if node_slot_id else None,
            farm_id=uuid.UUID(str(farm_id)) if farm_id else None,
            source="manual" if is_manual else "ai",
            state="open",
            duration_min=dur_per_cycle,
            mqtt_topic=None, # No longer needed for HTTP
            payload=payload,
            status="pending" if operating_mode != "shadow" else "shadow_skip",
        )
        db.add(cmd)

    elif action == "stop":
        if operating_mode == "shadow":
            logger.info(f"[controller] SHADOW MODE ACTIVE: Bypassing Stop Command.")
        else:
            # Create a stop command in DB for HTTP polling
            import uuid
            cmd = ValveCommand(
                id=uuid.uuid4(),
                zone_id=uuid.UUID(str(zone_id)) if zone_id else None,
                node_slot_id=uuid.UUID(str(node_slot_id)) if node_slot_id else None,
                farm_id=uuid.UUID(str(farm_id)) if farm_id else None,
                source="manual" if is_manual else "ai",
                state="closed",
                duration_min=0,
                mqtt_topic=None,
                payload={"action": "stop"},
                status="pending" if operating_mode != "shadow" else "shadow_skip",
            )
            db.add(cmd)

    # ── Step 3: Update ZoneState ─────────────────────────────────────────
    state_updates: Dict[str, Any] = {
        "current_moisture": final_decision.get("current_moisture"),
        "estimated_root_moisture": final_decision.get("estimated_root_moisture"),
        "predicted_moisture_1h": final_decision.get("predicted_1h"),
        "predicted_moisture_6h": final_decision.get("predicted_6h"),
        "predicted_moisture_24h": final_decision.get("predicted_24h"),
        "ai_recommendation": action,
        "model_confidence": confidence,
        "uncertainty_flag": final_decision.get("uncertainty_flag"),
        "execution_confidence": final_decision.get("execution_confidence", 1.0),
        "rolling_avg_24h": final_decision.get("rolling_avg_24h"),
        "current_stage": final_decision.get("stage"),
    }
    if action == "irrigate":
        state_updates["valve_state"] = "open"
        state_updates["last_irrigation_at"] = datetime.now(timezone.utc)
        state_updates["last_irrigation_duration"] = final_decision.get("duration_per_cycle_min", duration_min)
        
        # ── Perception Logic: Store Expected Gain ───────────────────────
        # Total water volume = cycles * (duration_per_cycle * rate)
        # Or simpler: get water_required_mm from the decision
        water_mm = final_decision.get("water_required_mm") or 0
        state_updates["expected_gain_mm"] = water_mm
        
        # Capture baseline for both safety (spike) and perception (reality check)
        current = final_decision.get("current_moisture")
        state_updates["moisture_at_irrigation_start"] = current
        state_updates["moisture_at_irrigation_end"] = current # Baseline for gain validation
        
    elif action in ("skip", "delay"):
        state_updates["valve_state"] = "closed"
        # Since we skipped, we reset the expectation (or keeping it if we want to check natural decay)
        state_updates["expected_gain_mm"] = 0

    await state_manager.update_zone_state(zone_id, state_updates, db)
    
    # ── Step 4: Log to Diary (for Subsidy) ──────────────────────────────────
    if action in ("irrigate", "irrigate_partial"):
        await diary_builder.log_activity(
            farm_id=farm_id,
            zone_id=zone_id,
            activity_type="irrigation",
            title=f"Irrigation: {action.replace('_', ' ').title()}",
            body=f"Applied {final_decision.get('applied_now_liters', 0)}L over {duration_min} minutes. Reason: {explanation_str}",
            metadata={
                "duration_min": duration_min,
                "liters": final_decision.get("applied_now_liters", 0),
                "moisture_before": final_decision.get("current_moisture"),
                "is_manual": is_manual,
                "decision_id": str(decision_record.id)
            },
            db=db,
            is_subsidy=True
        )

    await db.commit()

    return {
        "decision_id": decision_record.id,
        "decision": final_decision.get("decision", action),
        "action_now": final_decision.get("action_now", "SKIP"),
        "applied_now_mm": final_decision.get("applied_now_mm", 0.0),
        "applied_now_liters": final_decision.get("applied_now_liters", 0),
        "recovery_plan": final_decision.get("recovery_plan", []),
        "strategy": final_decision.get("strategy", "standard"),
        "soak_time_min": final_decision.get("soak_time_min", 0),
        "recheck_in": final_decision.get("recheck_in", "unknown"),
        "confidence": final_decision.get("confidence", confidence),
        "duration_min": duration_min,
        "mqtt_sent": mqtt_sent,
        "status": "executed",
        "policy_reason": final_decision.get("policy_reason"),
        "ood_flag": final_decision.get("ood_flag"),
        "top_factors": final_decision.get("top_factors"),
        "operating_mode": operating_mode,
        "uncertainty_flag": final_decision.get("uncertainty_flag"),
        "failed_node_mac": final_decision.get("failed_node_mac")
    }


async def emergency_abort(
    zone_id: str,
    farm_id: str,
    current_moisture: float,
    baseline_moisture: float,
    db: AsyncSession,
    master_mac: str = "",
) -> Dict[str, Any]:
    """
    The Safety Brake: Aborts active irrigation due to sudden moisture spike (Rain).
    """
    logger.warning(f"[safety] EMERGENCY ABORT zone={zone_id} spike={current_moisture - baseline_moisture:.1f}%")
    
    # 1. STOP via Command Queue
    cmd = ValveCommand(
        zone_id=zone_id,
        farm_id=farm_id,
        source="safety",
        state="closed",
        duration_min=0,
        mqtt_topic=None,
        payload={"action": "emergency_stop", "reason": "spike_detected"},
        status="pending"
    )
    db.add(cmd)
    
    # 2. Log Abortion
    decision_record = DecisionLog(
        zone_id=zone_id,
        decision="aborted",
        duration_min=0,
        explanation=f"SAFETY ABORT: Un-forecasted rain detected (Spike: {current_moisture - baseline_moisture:.1f}%).",
        policy_blocked=True,
        block_reason="safety_abort"
    )
    db.add(decision_record)
    
    # 3. Update State
    updates = {
        "valve_state": "closed",
        "uncertainty_flag": "rain_intercept",
        "ai_recommendation": "aborted"
    }
    await state_manager.update_zone_state(zone_id, updates, db)
    await db.commit()
    
    return {"status": "aborted"}


async def execute_manual_override(
    zone_id: str,
    farm_id: str,
    action: str,
    duration_min: int,
    reason: str,
    db: AsyncSession,
    master_mac: str = "",
    node_slot_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Manual override from user — bypasses AI but still logs."""
    override_decision = {
        "decision": action,
        "duration_min": duration_min,
        "target_moisture": None,
        "confidence": 1.0,
        "policy_applied": "manual_override",
        "policy_reason": reason,
        "feature_importance": {},
        "is_manual_override": True,
    }
    return await execute_decision(zone_id, farm_id, override_decision, db, master_mac, node_slot_id)

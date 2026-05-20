"""
Service — Intelligence Engine
Refactored core AI pipeline for reusability across API and MQTT.
"""
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.farm import Zone, Farm, NodeSlot
from backend.models.device import Device
from backend.models.sensor_data import SensorReading
from backend.plugins.ai.stage.stage_model import predict_stage
from backend.plugins.ai.prediction.lstm import predict_moisture
from backend.plugins.ai.decision.xgboost_engine import decide_irrigation
from backend.plugins.meta.policy import apply_policy_rules
from backend.plugins.meta.consistency import check_consistency, detect_sensor_anomaly
from backend.core.reliability.perception import (
    calculate_weighted_fusion, 
    detect_slow_drift, 
    validate_irrigation_gain, 
    correlate_zones
)
from backend.core.spatial.root_estimator import estimate_root_moisture, detect_depth_mismatch
from backend.core.reliability.control_loop import evaluate_mid_cycle
from backend.core.reliability.ml_supervisor import check_ood_bounds, extract_top_factors, calibrate_confidence
from backend.services.weather import get_weather
from backend.core.aggregation.aggregator import ZoneAggregator
from backend.control.controller import execute_decision, emergency_abort
from backend.utils.logger import logger
from backend.core.state.state_manager import state_manager
from backend.config.settings import get_settings

settings = get_settings()

async def process_telemetry_and_decide(
    farm_id: uuid.UUID,
    node_slot_readings: Dict[uuid.UUID, Dict[str, Any]],
    db: AsyncSession,
    rain_detected: bool = False
) -> List[Dict[str, Any]]:
    """
    The heart of AquaSol Intelligence. 
    Processes a batch of sensor data and returns a list of decisions.
    """
    results = []
    
    # Get farm info
    farm_res = await db.execute(select(Farm).where(Farm.id == farm_id))
    farm = farm_res.scalar_one_or_none()
    if not farm:
        logger.error(f"[intel] Farm not found {farm_id}")
        return []

    # ── 1. Weather Context ───────────────────────────────────────────
    weather = {}
    if farm.latitude and farm.longitude:
        weather = await get_weather(float(farm.latitude), float(farm.longitude))

    rain_mm = weather.get("rain_mm_6h", 0.0)
    rain_6h = weather.get("rain_prob_6h", 0.2)
    rain_24h = weather.get("rain_prob_24h", 0.3)

    # ── 2. Per-node AI pipeline ──────────────────────────────────────────
    for slot_id, ndata in node_slot_readings.items():
        moisture_raw = ndata.get("moisture") or 50.0
        trust_initial = ndata.get("trust_score") or 1.0
        
        # Get topology for this slot
        slot_res = await db.execute(
            select(NodeSlot).where(NodeSlot.id == slot_id)
        )
        slot = slot_res.scalar_one_or_none()
        if not slot: continue
        zone_id = slot.zone_id

        zone_state = await state_manager.get_zone_state(str(zone_id), db)
        
        # B: Hydraulic Continuity Guard (Drift Detection)
        # Fetch previous moisture from DB state
        prev_moisture = zone_state.get("current_moisture") if zone_state else None
        last_update = zone_state.get("updated_at") if zone_state else None
        
        # Check for Anomaly
        soil_type = "loam"
        crop_type = "Tomato"
        zone_res = await db.execute(select(Zone).where(Zone.id == zone_id))
        zone = zone_res.scalar_one_or_none()
        if zone:
            soil_type = zone.soil_type or "loam"
            crop_type = zone.crop_type or "Tomato"
        else:
            continue
            
        from backend.plugins.meta.bio_engine import CropProfileLoader
        profile = await CropProfileLoader.get_profile(db, crop_type)
        if not profile:
            logger.warning(f"No DB profile for {crop_type}, fallback to Tomato")
            profile = await CropProfileLoader.get_profile(db, "Tomato")
            if not profile:
                logger.error("SYSTEM FATAL: Tomato fallback missing in DB!")
                continue
        
        # 1. Rapid Anomaly Check (v2 — full multi-layer engine)
        anomaly = detect_sensor_anomaly(
            current_moisture=moisture_raw,
            previous_moisture=prev_moisture,
            last_updated_at=last_update,
            soil_type=soil_type,
            settings=settings,
            temperature=ndata.get("temperature"),
            humidity=ndata.get("humidity"),
            zone_id=str(zone_id),
        )
        
        # 2. Slow Drift Check
        slow_drift = detect_slow_drift(
            moisture_raw, zone_state.get("rolling_avg_24h") if zone_state else None
        )
        
        # A: Performance Validation (Hydraulic Gain Check)
        irrigation_veto = False
        if zone_state and (zone_state.get("expected_gain_mm") or 0) > 0:
            moisture_start = zone_state.get("moisture_at_irrigation_end") # This is actually the baseline end of last cycle
            actual_gain = float(moisture_raw) - float(moisture_start) if moisture_start else 0
            
            # We only check if it's been enough time for soaking
            validation = validate_irrigation_gain(
                actual_gain, 
                float(zone_state.get("expected_gain_mm")), 
                soil_type, 
                settings.STAGE_ROOT_DEPTH.get("default", 300)
            )
            if not validation["is_valid"]:
                logger.error(f"[perception] IRRIGATION VETO in zone {zone_id}: {validation['deviation']}% deficit in moisture gain.")
                irrigation_veto = "delivery_failure"

        # Check for Node Failure (Heartbeat & DB backup)
        node_status = "online"
        res_device = await db.execute(
            select(Device)
            .join(NodeSlot, NodeSlot.id == Device.node_slot_id)
            .where(NodeSlot.zone_id == zone_id)
            .limit(1)
        )
        device_row = res_device.scalar_one_or_none()
        if device_row:
            # Check dynamic last_seen freshness (5 minutes threshold)
            if device_row.last_seen_at:
                delta = (datetime.now(timezone.utc) - device_row.last_seen_at).total_seconds() / 60
                if delta > 5.0:
                    node_status = "failed"
                else:
                    node_status = "online"
            else:
                node_status = "failed"

        uncertainty_flag = None
        trust_score = trust_initial
        if node_status == "failed":
            trust_score = 0.0
            uncertainty_flag = "node_failure"
            logger.warning(f"[intel] Node {device_row.mac_address if device_row else 'Unknown'} FAILED. Activating Virtual Sensing.")
            
            from backend.services.alerts import create_alert
            # Create Node Offline Alert
            await create_alert(
                farm_id=str(farm_id),
                zone_id=str(zone_id),
                alert_type="node_failure",
                title="📡 Node Offline Alert",
                description=f"Device {device_row.node_label if device_row else 'Unknown'} ({device_row.mac_address if device_row else 'Unknown'}) is offline. System failing over to Virtual Sensing.",
                db=db
            )
        elif anomaly["is_anomaly"]:
            trust_score = settings.DRIFT_PENALTY_TRUST_SCORE
            uncertainty_flag = "sensor_drift"
            
            from backend.services.alerts import create_alert, build_anomaly_alert
            # Create Sensor Anomaly Alert
            alert_data = build_anomaly_alert(
                node_label=device_row.node_label if device_row else "Unknown",
                sensor="moisture",
                value=moisture_raw,
                anomaly_type=anomaly.get("anomaly_type") or "unknown",
                is_virtual=False
            )
            await create_alert(
                farm_id=str(farm_id),
                zone_id=str(zone_id),
                alert_type="anomaly",
                title=alert_data["title"],
                description=alert_data["description"],
                db=db
            )
        elif slow_drift["is_anomaly"]:
            trust_score = settings.DRIFT_PENALTY_TRUST_SCORE * 2
            uncertainty_flag = "slow_drift"
            
            from backend.services.alerts import create_alert
            # Create Slow Drift Alert
            await create_alert(
                farm_id=str(farm_id),
                zone_id=str(zone_id),
                alert_type="anomaly",
                title="⚠️ Sensor Drift Warning",
                description=f"Moisture reading on Node {device_row.node_label if device_row else 'Unknown'} shows slow drift. Recalibration recommended.",
                db=db
            )
        elif irrigation_veto:
            trust_score = 0.05
            uncertainty_flag = "delivery_failure"
            
            from backend.services.alerts import create_alert
            # Create Delivery Failure Alert
            await create_alert(
                farm_id=str(farm_id),
                zone_id=str(zone_id),
                alert_type="anomaly",
                title="❌ Valve Delivery Failure",
                description=f"Irrigation run in zone {zone_id} failed to produce expected soil moisture gain. Please check valve plumbing.",
                db=db
            )
            
        # Recovery Logic: Gradually restore trust if reading stays dry/stable (User Request)
        if uncertainty_flag and node_status == "online" and not (anomaly["is_anomaly"] or slow_drift["is_anomaly"]):
            can_recover = not rain_detected and rain_mm <= 0.0
            if can_recover:
                trust_score = min(1.0, trust_score + settings.TRUST_RECOVERY_RATE)
                if trust_score >= 0.8: uncertainty_flag = None
        
        failed_mac = device_row.mac_address if uncertainty_flag == "node_failure" and device_row else None

        if uncertainty_flag == "node_failure":
             from backend.services.alerts import create_alert
             await create_alert(
                 farm_id=str(farm_id),
                 zone_id=str(zone_id),
                 alert_type="virtual_sensing",
                 title="Virtual Sensing Active",
                 description=f"Node {device_row.mac_address if device_row else 'Unknown'} is offline. Using AI estimation.",
                 db=db
             )

        # 4. Closed-Loop Control (Mid-Cycle Evaluation)
        execution_confidence = 1.0
        if zone_state and zone_state.get("valve_state") == "open":
            mid_cycle_res = evaluate_mid_cycle(
                zone_state, moisture_raw, soil_type, grace_period_minutes=15
            )
            execution_confidence = mid_cycle_res.get("confidence", 1.0)
            
            # Execute early stop or abort
            if mid_cycle_res["action"] != "continue":
                # Resolve master for mid-cycle stop
                mc_res = await db.execute(select(Device).where(Device.farm_id == farm_id, Device.is_master == True).limit(1))
                mc_dev = mc_res.scalar_one_or_none()
                mc_mac = mc_dev.mac_address if mc_dev else ""
                
                abort_res = await execute_decision(
                    zone_id=str(zone_id),
                    farm_id=str(farm_id),
                    final_decision={
                        "decision": "stop",
                        "policy_reason": f"Closed-Loop Action: {mid_cycle_res['reason']}",
                        "confidence": mid_cycle_res.get("confidence", 1.0),
                        "execution_confidence": execution_confidence,
                        "uncertainty_flag": "delivery_failure" if "flow_failure" in mid_cycle_res["action"] else uncertainty_flag
                    },
                    db=db,
                    master_mac=mc_mac
                )
                results.append(abort_res)
                continue # Bypass the rest of the AI pipeline for this zone
            
            # Legacy Safety A: Check for Forecast Failure (Safety Brake) - Still useful for immediate spikes
            baseline = zone_state.get("moisture_at_irrigation_start")
            if baseline is not None:
                spike = float(moisture_raw) - float(baseline)
                if spike >= settings.ABORT_SPIKE_THRESHOLD_PCT:
                    # Resolve master for emergency stop
                    m_res = await db.execute(select(Device).where(Device.farm_id == farm_id, Device.is_master == True).limit(1))
                    m_dev = m_res.scalar_one_or_none()
                    m_mac = m_dev.mac_address if m_dev else ""
                    
                    abort_res = await emergency_abort(
                        str(zone_id), str(farm_id), moisture_raw, baseline, db, master_mac=m_mac
                    )
                    results.append(abort_res)
                    continue

        # DAP Calculation with safety
        sowing = zone.sowing_date or (datetime.now(timezone.utc).date())
        dap = (datetime.now(timezone.utc).date() - sowing).days

        # A. Stage prediction (Refined Rule-Based Engine)
        try:
            logger.info(f"[intel] Predict Stage for {zone.crop_type} | DAP: {dap} | Moisture: {moisture_raw}")
            stage_result = predict_stage(
                crop=zone.crop_type or "Rice", 
                season="kharif", 
                days_after_planting=dap,
                soil_moisture_avg_24h=moisture_raw,
                total_duration_days=profile.get("duration", 150)
            )
            logger.info(f"[intel] Predicted Stage: {stage_result.get('stage')}")
        except Exception as stage_err:
            logger.error(f"[intel] predict_stage FAILED: {stage_err} | DAP: {dap} type={type(dap)} | Duration: {profile.get('duration')} type={type(profile.get('duration'))}")
            raise stage_err

        # B. Prediction (For Fusion)
        prediction = predict_moisture(
            recent_readings=[],
            current_moisture=moisture_raw,
            temperature=ndata.get("temperature") or 28.0,
            humidity=ndata.get("humidity") or 65.0,
            rain_prob=rain_6h,
        )
        
        # ── Weighted Perception Fusion ─────────────────────────────────────
        # Instead of binary trust, we fuse sensor with LSTM model
        moisture_fused = calculate_weighted_fusion(
            moisture_raw, 
            prediction.get("predicted_1h", moisture_raw), 
            trust_score
        )
        
        # ── Spatial Reasoning (Root-Zone Estimation) ───────────────────────
        temp_now = ndata.get("temperature") or 28.0
        estimated_root = estimate_root_moisture(moisture_fused, soil_type, temp_now)
        depth_mismatch = detect_depth_mismatch(zone.sensor_depth_cm or 10, zone.root_depth_cm or 30)
        
        logger.info(f"[spatial] Zone {zone_id}: Fused={moisture_fused}% Estimated_Root={estimated_root}% Mismatch={depth_mismatch}")

        # ── Crop Planner Integration ──────────────────────────────────────
        # Check if there is a manual plan for this zone/week
        from backend.models.decision import CropPlan
        from sqlalchemy import desc
        plan_res = await db.execute(
            select(CropPlan).where(CropPlan.zone_id == str(zone_id))
            .order_by(desc(CropPlan.created_at)).limit(1)
        )
        latest_plan = plan_res.scalar_one_or_none()
        plan_recommendation = None
        if latest_plan and latest_plan.weekly_plan:
            current_week = (dap // 7) + 1
            # Find matching week in plan
            for entry in (latest_plan.weekly_plan or []):
                if entry.get("week") == current_week:
                    plan_recommendation = entry
                    break
        
        if plan_recommendation:
            logger.info(f"[planner] Applying plan for Week {current_week}: {plan_recommendation.get('task')}")

        # C. XGBoost decision (Now using Estimated Root Moisture)
        t_min = float(zone.min_moisture_threshold or 40.0)
        t_max = float(zone.max_moisture_threshold or 80.0)
        
        is_ood = check_ood_bounds(estimated_root, temp_now)
        if is_ood:
            logger.warning(f"[ml_supervisor] OOD Bounds Breached for Zone {zone_id}. Forcing Guardrail delay.")

        inference_decision = decide_irrigation(
            current_moisture=estimated_root,
            predicted_moisture_6h=prediction.get("predicted_6h", estimated_root),
            predicted_moisture_24h=prediction.get("predicted_24h", estimated_root),
            target_moisture_min=t_min,
            target_moisture_max=t_max,
            days_after_planting=dap,
            weather_rain_prob_6h=rain_6h,
            weather_rain_prob_24h=rain_24h,
            last_irrigation_hours_ago=24.0,
            temperature_avg_6h=ndata.get("temperature") or 28.0,
            humidity_avg_6h=ndata.get("humidity") or 65.0,
            trust_score_avg_zone=trust_score,
            soil_type_encoded=1 if soil_type == "loam" else (2 if soil_type == "clay" else 0),
            profile=profile
        )

        # D. Policy Intelligence (Now using Estimated Root Moisture)
        final_decision = apply_policy_rules(
            decision=inference_decision,
            rain_mm=rain_mm,
            trust_score=trust_score,
            last_irrigation_hours_ago=24.0,
            hour_of_day=datetime.now().hour,
            current_moisture=estimated_root,
            predicted_moisture_6h=prediction.get("predicted_6h", estimated_root),
            target_moisture_min=t_min,
            soil_type=soil_type,
            crop_stage=stage_result.get("stage") or "vegetative",
            app_rate=float(zone.application_rate_mm_hr or 2.0),
            efficiency=float(zone.efficiency or 0.9),
            crop_type=zone.crop_type or "Maize",
            # Pass spatial context into policy for overrides
            depth_mismatch=depth_mismatch,
            surface_moisture=moisture_fused,
            is_ood=is_ood,
            rolling_24h_mm=float(zone_state.get("rolling_24h_mm", 0.0)),
            temperature=temp_now,
            humidity=ndata.get("humidity") or 65.0,
            area_acres=float(zone.area_acres or 1.0),
            plan_recommendation=plan_recommendation
        )
        
        # Extract Explainability
        if "feature_importance" in inference_decision:
            from backend.plugins.ai.decision.xgboost_engine import FEATURE_NAMES
            top_factors = extract_top_factors(inference_decision["feature_importance"], FEATURE_NAMES)
            final_decision["top_factors"] = top_factors
            
        final_decision["ood_flag"] = is_ood

        # E. Consistency & Adjustment
        checked = check_consistency(final_decision, stage_result, prediction, estimated_root)
        validated_decision = checked["adjusted_decision"]
        
        # Calculate new rolling average
        old_rolling = float(zone_state.get("rolling_avg_24h") or moisture_raw)
        new_rolling = (old_rolling * 0.95) + (moisture_raw * 0.05) if moisture_raw else old_rolling

        validated_decision.update({
            "current_moisture": moisture_raw,
            "fused_moisture": moisture_fused,
            "estimated_root_moisture": estimated_root,
            "predicted_6h": prediction.get("predicted_6h"),
            "predicted_24h": prediction.get("predicted_24h"),
            "rain_prob_6h": rain_6h,
            "stage": stage_result.get("stage"),
            "target_moisture": t_min,
            "uncertainty_flag": uncertainty_flag,
            "failed_node_mac": failed_mac,
            "rolling_avg_24h": new_rolling,
            "operating_mode": zone.operating_mode or "active",
            "active_plan_task": plan_recommendation.get("tasks") if plan_recommendation else None
        })

        # Safety Skip: If delivery failure is suspected, stop all automated irrigation
        if uncertainty_flag == "delivery_failure":
            validated_decision["decision"] = "delay"
            validated_decision["policy_reason"] = "CRITICAL: Moisture response failure detected. Field check required."

        # F. Execution
        # Find the master device for this farm to route the command
        master_res = await db.execute(
            select(Device).where(Device.farm_id == farm_id, Device.is_master == True).limit(1)
        )
        master_device = master_res.scalar_one_or_none()
        master_mac_val = master_device.mac_address if master_device else ""

        exec_res = await execute_decision(
            zone_id=str(zone_id),
            farm_id=str(farm_id),
            final_decision=validated_decision,
            db=db,
            master_mac=master_mac_val,
            node_slot_id=str(slot_id)
        )
        results.append(exec_res)

    return results

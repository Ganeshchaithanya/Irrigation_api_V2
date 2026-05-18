"""
API - Sensors
Endpoint for Master nodes to POST telemetry batches (Unified HTTP Ingestion).
"""
import uuid
import secrets
from typing import List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.device import Device
from backend.models.pairing_session import PairingSession
from backend.models.user import User
from backend.models.farm import Farm, NodeSlot
from backend.models.sensor_data import SensorReading
from backend.schemas.sensor import SensorBatch, TelemetryResponse
from backend.core.reliability.anomaly import detect_anomaly
from backend.core.aggregation.aggregator import ZoneAggregator
from backend.services.intelligence_engine import process_telemetry_and_decide
from backend.utils.logger import logger
from backend.services.health_monitor import health_monitor
from backend.models.decision import ValveCommand
from backend.core.state.state_manager import state_manager
from backend.app.dependencies import get_current_user

router = APIRouter(prefix="/sensors", tags=["sensors"])

@router.post("", response_model=TelemetryResponse)
async def ingest_sensors(
    request: Request,
    batch: SensorBatch,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests a batch of readings from a Master Node (Proxy).
    """
    # Log raw body for debugging formatting issues
    raw_body = await request.body()
    logger.info(f"[sensors] Raw Payload from {batch.master_mac}: {raw_body.decode()}")
    logger.info(
        f"[sensors] Node moisture values: "
        + ", ".join(
            f"{e.node_mac}={e.soil_moisture}"
            for e in batch.events
            if e.node_mac != batch.master_mac
        )
    )

    # Normalize codes
    batch_code = batch.pairing_code.upper() if batch.pairing_code else None

    # 1. Resolve Master
    res = await db.execute(
        select(Device).where(
            Device.mac_address == batch.master_mac, 
            Device.is_master == True
        )
    )
    master = res.scalar_one_or_none()
    
    if master and batch_code:
        master.pairing_code = batch_code

    if not master:
        logger.info(f"[sensors] Auto-discovering Master MAC: {batch.master_mac} Code: {batch_code}")
        
        # Check for an active PairingSession (App claim)
        session = None
        if batch_code:
            session_res = await db.execute(
                select(PairingSession).where(
                    PairingSession.pairing_code == batch_code,
                    PairingSession.is_used == False,
                    PairingSession.expires_at > datetime.now(timezone.utc)
                )
            )
            session = session_res.scalar_one_or_none()
        
        target_farm_id = session.farm_id if session else None
        
        master = Device(
            id=uuid.uuid4(),
            device_uid=f"MST-{batch.master_mac.replace(':', '')}",
            mac_address=batch.master_mac,
            pairing_code=batch_code,
            farm_id=target_farm_id,
            is_master=True,
            role="master",
            status="active" if target_farm_id else "discovery",
            is_claimed=True if target_farm_id else False,
            node_label="Main Controller" if target_farm_id else "Unassigned Master",
            last_seen_at=datetime.now(timezone.utc)
        )
        db.add(master)
        
        if session:
            session.is_used = True
            session.device_id = master.id
            
        await db.flush()
    else:
        master.last_seen_at = datetime.now(timezone.utc)
        # Try to pair/re-pair if session exists
        session = None
        if batch_code:
            session_res = await db.execute(
                select(PairingSession).where(
                    PairingSession.pairing_code == batch_code,
                    PairingSession.is_used == False,
                    PairingSession.expires_at > datetime.now(timezone.utc)
                )
            )
            session = session_res.scalar_one_or_none()
            
        if session:
            logger.info(f"[sensors] Pairing/Updating Master {batch.master_mac} to Farm {session.farm_id}")
            master.farm_id = session.farm_id
            master.status = "active"
            master.is_claimed = True
            master.node_label = "Main Controller"
            session.is_used = True
            session.device_id = master.id
            await db.flush()

    farm_id = master.farm_id
    
    # 2. Process Events
    zone_aggregates: Dict[uuid.UUID, ZoneAggregator] = {}
    node_slot_readings: Dict[uuid.UUID, Dict[str, Any]] = {}
    
    for event in batch.events:
        if event.node_mac == batch.master_mac:
            continue
            
        # Normalize Node Code
        node_code = event.pairing_code.upper() if event.pairing_code else event.node_mac.replace(":", "")[-6:].upper()

        # Resolve or Auto-Create node by MAC
        res = await db.execute(
            select(Device)
            .options(selectinload(Device.node_slot))
            .where(Device.mac_address == event.node_mac)
        )
        device = res.scalar_one_or_none()
        
        if device and node_code:
            device.pairing_code = node_code

        if not device:
            logger.info(f"[sensors] Auto-discovering Node MAC: {event.node_mac} Code: {node_code}")
            
            # Check for an active PairingSession for this node
            session = None
            if node_code:
                session_res = await db.execute(
                    select(PairingSession).where(
                        PairingSession.pairing_code == node_code,
                        PairingSession.is_used == False,
                        PairingSession.expires_at > datetime.now(timezone.utc)
                    )
                )
                session = session_res.scalar_one_or_none()
            
            target_farm_id = session.farm_id if session else None
            target_zone_id = session.zone_id if session else None
            
            device = Device(
                id=uuid.uuid4(),
                device_uid=f"NOD-{event.node_mac.replace(':', '')}",
                mac_address=event.node_mac,
                pairing_code=node_code,
                farm_id=target_farm_id,
                node_slot_id=session.node_slot_id if session else None,
                is_master=False,
                role="node",
                status="active" if target_farm_id else "discovery",
                is_claimed=True if target_farm_id else False,
                node_label="Acre Node" if target_farm_id else "Unassigned Node",
                last_seen_at=datetime.now(timezone.utc)
            )
            db.add(device)
            
            if session:
                session.is_used = True
                session.device_id = device.id
                # If we have a zone/slot in mind, we'd bind it here too
                
            await db.flush()
        else:
            device.last_seen_at = datetime.now(timezone.utc)
            # Try to pair/re-pair if session exists
            session = None
            if node_code:
                session_res = await db.execute(
                    select(PairingSession).where(
                        PairingSession.pairing_code == node_code,
                        PairingSession.is_used == False,
                        PairingSession.expires_at > datetime.now(timezone.utc)
                    )
                )
                session = session_res.scalar_one_or_none()
                
            if session:
                logger.info(f"[sensors] Pairing/Updating Node {event.node_mac} to Farm {session.farm_id}")
                device.farm_id = session.farm_id
                device.node_slot_id = session.node_slot_id
                device.status = "active"
                device.is_claimed = True
                device.node_label = "Acre Node"
                session.is_used = True
                session.device_id = device.id
                await db.flush()

        # Resolve logical topology
        zone_id = None
        node_slot_id = device.node_slot_id
        
        # Safely fetch zone_id since async SQLAlchemy doesn't lazy load relationships
        if node_slot_id:
            slot_res = await db.execute(select(NodeSlot.zone_id).where(NodeSlot.id == node_slot_id))
            zone_id = slot_res.scalar_one_or_none()

        # If node is unassigned to a slot, we still record data but skip AI aggregation
        if not zone_id or not farm_id:
            continue 

        # Aggregate for AI Decision
        if zone_id not in zone_aggregates:
            zone_aggregates[zone_id] = ZoneAggregator(zone_id)
        
        # Record heartbeat for health monitoring
        health_monitor.update_node_freshness(event.node_mac)
        state_manager.record_heartbeat(event.node_mac)

        # Update Zone State will happen after loop for aggregation

        # Anomaly detection (isolation forest fallback)
        anomaly = detect_anomaly(
            soil_moisture=event.soil_moisture,
            temperature=event.temperature,
            humidity=event.humidity
        )

        # --- Normalization guard ---
        # Some firmware revisions send soil_moisture as a 0–1 fraction instead of 0–100.
        # Detect this and auto-scale to maintain data consistency.
        raw_moisture = event.soil_moisture
        if raw_moisture is not None and raw_moisture <= 1.0 and raw_moisture >= 0.0:
            logger.warning(
                f"[sensors] Node {event.node_mac} sent soil_moisture={raw_moisture} "
                f"(fraction detected — scaling ×100 to {raw_moisture * 100:.1f})"
            )
            raw_moisture = raw_moisture * 100.0

        reading = SensorReading(
            time=datetime.now(timezone.utc),
            device_id=device.id,
            node_slot_id=node_slot_id,
            zone_id=zone_id,
            farm_id=farm_id,
            soil_moisture=raw_moisture,
            temperature=event.temperature,
            humidity=event.humidity,
            valve_status=(event.valve_status == 1),
            battery_pct=event.battery_pct,
            solar_pct=event.solar_pct,
            
            # Master sensors from root of batch
            flow_rate=batch.flow_rate,
            total_water=batch.total_water,
            rain_detected=(batch.rain_detected == 1),
            solar_voltage=batch.solar_voltage,
        )
        db.add(reading)
        
        zone_aggregates[zone_id].add_reading(raw_moisture, event.temperature, event.humidity, float(device.trust_score or 1.0))
        
        node_slot_readings[node_slot_id] = {
            "moisture": raw_moisture,
            "temperature": event.temperature,
            "humidity": event.humidity,
            "valve_status": event.valve_status,
            "mac_address": event.node_mac,
            "trust_score": float(device.trust_score or 1.0)
        }

    await db.flush()

    # 3. Update Zone States with aggregated data
    for zid, agg in zone_aggregates.items():
        computed = agg.compute()
        await state_manager.update_zone_state(str(zid), {
            "current_moisture": computed["soil_moisture_avg"],
            "weather_temp": computed["temperature_avg"],
            "humidity_avg": computed["humidity_avg"],
            "trust_score_avg": computed["trust_score_avg"],
        }, db)

    # 4. Finalize and Return
    if not farm_id:
        logger.info(f"[sensors] Master {batch.master_mac} is in discovery mode. Skipping intel.")
        return {
            "status": "ok",
            "processed_count": 0,
            "commands": [],
            "intel": []
        }

    try:
        # 4. Trigger AI Decision Engine
        intel_results = await process_telemetry_and_decide(
            farm_id, 
            node_slot_readings, 
            db,
            rain_detected=(batch.rain_detected == 1)
        )
        
        # Corrected Join: Devices -> NodeSlot -> ValveCommand
        # We join Device to NodeSlot first, then check if the command matches the slot OR the zone
        
        cmd_result = await db.execute(
            select(ValveCommand, Device.mac_address)
            .join(NodeSlot, Device.node_slot_id == NodeSlot.id)
            .join(
                ValveCommand,
                or_(
                    ValveCommand.node_slot_id == NodeSlot.id,
                    and_(ValveCommand.node_slot_id.is_(None), ValveCommand.zone_id == NodeSlot.zone_id)
                )
            )
            .where(
                ValveCommand.farm_id == farm_id,
                ValveCommand.status == "pending"
            )
        )
        rows = cmd_result.all()
        
        pending_payloads = []
        node_targets = {}
        
        for cmd, mac in rows:
            pending_payloads.append({
                "id": str(cmd.id),
                "node_mac": mac or "",
                "action": cmd.state,
                "payload": cmd.payload
            })
            if mac:
                node_targets[mac] = (cmd.state == "open")
            
            cmd.status = "published"
            cmd.sent_at = datetime.now(timezone.utc)
            
        # 3. Record Master's own metrics (Flow, Rain, etc.)
        if farm_id:
            master_reading = SensorReading(
                time=datetime.now(timezone.utc),
                device_id=master.id,
                zone_id=None, # Master-only readings are farm-wide
                farm_id=farm_id,
                flow_rate=batch.flow_rate,
                total_water=batch.total_water,
                rain_detected=(batch.rain_detected == 1),
                solar_voltage=batch.solar_voltage,
                battery_pct=batch.battery_pct,
                solar_pct=batch.solar_pct,
                is_virtual=False
            )
            db.add(master_reading)

        await db.commit()

        vs_active = any(res.get("uncertainty_flag") == "node_failure" for res in intel_results)
        failed_nodes = [res.get("failed_node_mac") for res in intel_results if res.get("uncertainty_flag") == "node_failure"]

        return {
            "status": "success",
            "processed_count": len(batch.events),
            "commands": pending_payloads,
            "node_targets": node_targets,
            "virtual_sensing_active": vs_active,
            "failed_nodes": failed_nodes,
            "message": "Telemetry processed successfully"
        }

    except Exception as e:
        import traceback
        await db.rollback()
        logger.error(f"[sensors] Commit failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Data persistence failed: {e}")


@router.get("/history")
async def get_farm_sensor_history(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch the latest sensor readings across the entire farm."""
    # 1. Resolve Farm
    farm_res = await db.execute(select(Farm).where(Farm.user_id == current_user.id))
    farm = farm_res.scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    # 2. Fetch Readings with Device info
    result = await db.execute(
        select(SensorReading, Device.mac_address, Device.node_label, Device.is_master)
        .join(Device, Device.id == SensorReading.device_id)
        .where(SensorReading.farm_id == farm.id)
        .order_by(desc(SensorReading.time))
        .limit(limit)
    )
    rows = result.all()

    history = []
    for r, mac, label, is_master in rows:
        history.append({
            "time": r.time.isoformat(),
            "mac": mac,
            "label": label or ("Master" if is_master else "Node"),
            "soil_moisture": r.soil_moisture,
            "temperature": r.temperature,
            "humidity": r.humidity,
            "flow_rate": r.flow_rate,
            "rain_detected": r.rain_detected,
            "battery": r.battery_pct,
            "is_master": is_master
        })

    return history

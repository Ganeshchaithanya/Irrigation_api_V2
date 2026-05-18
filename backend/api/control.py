"""
API Router — Manual Override & Commands
POST /override          → manual irrigate/stop
GET  /commands          → ESP32 polls pending commands
POST /commands/{id}/ack → ESP32 acknowledges command
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_, and_
from datetime import datetime, timezone
from typing import List

from backend.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.models.user import User
from backend.models.farm import Farm, Zone, Acre
from backend.models.decision import ValveCommand, Schedule
from backend.models.device import Device
from backend.control.controller import execute_manual_override
from backend.schemas.dashboard import OverrideRequest, AcreOverrideRequest, ScheduleCreate, AdvisoryActionRequest
from backend.utils.logger import logger

router = APIRouter(prefix="/control", tags=["Control & Commands"])


@router.post("/override")
async def manual_override(
    payload: OverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manual valve control — bypasses AI, logged as manual override."""
    farm_result = await db.execute(
        select(Farm).where(Farm.user_id == current_user.id)
    )
    farm = farm_result.scalar_one_or_none()
    if not farm:
        raise HTTPException(404, "No farm found.")

    if payload.action not in ("irrigate", "stop"):
        raise HTTPException(400, "action must be 'irrigate' or 'stop'.")

    result = await execute_manual_override(
        zone_id=str(payload.zone_id),
        node_slot_id=str(payload.node_slot_id) if payload.node_slot_id else None,
        farm_id=str(farm.id),
        action=payload.action,
        duration_min=payload.duration_min,
        reason=payload.reason or "Manual override by farmer",
        db=db,
    )
    logger.info(f"[override] User {current_user.id} → {payload.action} zone {payload.zone_id}")
    return {"status": "ok", **result}


@router.get("/commands")
async def get_pending_commands(
    mac_address: str,
    db: AsyncSession = Depends(get_db),
):
    """
    ESP32 master polls this endpoint for pending commands using its MAC address.
    """
    res = await db.execute(
        select(Device).where(Device.mac_address == mac_address, Device.is_master == True)
    )
    master = res.scalar_one_or_none()
    if not master:
        raise HTTPException(403, "Invalid master MAC address.")

    farm_id = master.farm_id

    from backend.models.farm import NodeSlot
    
    cmd_result = await db.execute(
        select(ValveCommand, Device.mac_address)
        .join(NodeSlot, Device.node_slot_id == NodeSlot.id)
        .join(
            ValveCommand,
            or_(
                ValveCommand.node_slot_id == NodeSlot.id,
                and_(ValveCommand.node_slot_id.is_(None), ValveCommand.zone_id == NodeSlot.zone_id)
            )
        ).where(
            ValveCommand.farm_id == farm_id,
            ValveCommand.status == "pending"
        ).limit(5)
    )
    rows = cmd_result.all()

    if not rows:
        return {}

    # Get the oldest pending command
    c, mac = rows[0]
    c.status = "published"
    c.sent_at = datetime.now(timezone.utc)
    
    # Map backend actions to Firmware v3 expected strings
    action_map = {
        "open": "START_IRRIGATION",
        "closed": "STOP_IRRIGATION",
        "irrigate": "START_IRRIGATION",
        "stop": "STOP_IRRIGATION"
    }

    # Identify if it's Zone 1 or 2 based on the hardcoded Node MACs in Firmware v3
    # In a fully dynamic system we would fetch this, but for v3 strict order:
    zone_num = 1 if mac == "E0:8C:FE:34:1B:18" else 2 if mac == "28:05:A5:24:D6:08" else 0

    response = {
        "action": action_map.get(c.state, "SKIP"),
        "command_id": str(c.id),
        "zone": zone_num
    }

    await db.flush()
    await db.commit()

    return response

@router.post("/commands/{command_id}/ack")
async def acknowledge_command(
    command_id: str,
    master_mac: str,
    db: AsyncSession = Depends(get_db),
):
    """ESP32 ACKs command execution using its MAC address."""
    res = await db.execute(
        select(Device).where(Device.mac_address == master_mac, Device.is_master == True)
    )
    master = res.scalar_one_or_none()
    if not master:
        raise HTTPException(403, "Invalid master MAC address.")

    cmd_result = await db.execute(
        select(ValveCommand).where(ValveCommand.id == command_id, ValveCommand.farm_id == master.farm_id)
    )
    cmd = cmd_result.scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found.")

    cmd.status = "acked"
    cmd.acked_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "acknowledged", "command_id": command_id}

@router.post("/ack")
async def acknowledge_command_flat(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """ESP32 ACKs command using flat JSON payload {command_id: ..., status: ...}."""
    command_id = payload.get("command_id")
    status = payload.get("status")
    
    if not command_id:
        raise HTTPException(400, "Missing command_id")

    cmd_result = await db.execute(
        select(ValveCommand).where(ValveCommand.id == command_id)
    )
    cmd = cmd_result.scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found.")

    cmd.status = "acked"
    cmd.acked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "acknowledged", "command_id": command_id}


@router.post("/acre_override")
async def acre_override(
    payload: AcreOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manual valve control for all zones in an acre."""
    # Verify acre belongs to user
    res = await db.execute(
        select(Acre).join(Farm).where(Acre.id == payload.acre_id, Farm.user_id == current_user.id)
    )
    acre = res.scalar_one_or_none()
    if not acre:
        raise HTTPException(404, "Acre not found or access denied.")

    # Get all zones for this acre
    z_res = await db.execute(select(Zone).where(Zone.acre_id == acre.id))
    zones = z_res.scalars().all()

    results = []
    for zone in zones:
        res = await execute_manual_override(
            zone_id=str(zone.id),
            farm_id=str(acre.farm_id),
            action=payload.action,
            duration_min=payload.duration_min,
            reason=payload.reason or f"Acre-wide override: {acre.name}",
            db=db,
        )
        results.append({"zone_id": str(zone.id), "status": res.get("status")})

    return {"status": "ok", "acre_id": str(payload.acre_id), "zones": results}


@router.get("/schedules")
async def get_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch all schedules for user's farm."""
    res = await db.execute(
        select(Schedule).join(Farm).where(Farm.user_id == current_user.id)
    )
    return res.scalars().all()


@router.post("/schedules")
async def create_schedule(
    payload: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new irrigation schedule."""
    # Find farm_id
    f_res = await db.execute(select(Farm).where(Farm.user_id == current_user.id))
    farm = f_res.scalar_one_or_none()
    if not farm:
        raise HTTPException(404, "Farm not found")

    new_schedule = Schedule(
        id=uuid.uuid4(),
        farm_id=farm.id,
        zone_id=payload.zone_id,
        acre_id=payload.acre_id,
        label=payload.label,
        time=payload.time,
        days=payload.days,
        duration_min=payload.duration_min,
        intensity=payload.intensity,
        mode=payload.mode,
        is_active=payload.is_active
    )
    db.add(new_schedule)
    await db.commit()
    return new_schedule


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a schedule."""
    res = await db.execute(
        select(Schedule).join(Farm).where(Schedule.id == schedule_id, Farm.user_id == current_user.id)
    )
    schedule = res.scalar_one_or_none()
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    await db.delete(schedule)
    await db.commit()
    return {"status": "deleted"}

@router.post("/advisory-action")
async def handle_advisory_action(
    payload: AdvisoryActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve or dismiss an AI recommendation."""
    # Find farm for user
    f_res = await db.execute(select(Farm).where(Farm.user_id == current_user.id))
    farm = f_res.scalar_one_or_none()
    if not farm:
        raise HTTPException(404, "Farm not found")

    if payload.action == "approve":
        # Execute the recommendation as an override
        result = await execute_manual_override(
            zone_id=str(payload.zone_id),
            farm_id=str(farm.id),
            action="irrigate",
            duration_min=15, # Default, could be from decision_id if tracked
            reason="AI Advisory Approved",
            db=db,
        )
        logger.info(f"[advisory] User {current_user.id} APPROVED advisory for zone {payload.zone_id}")
        return {"status": "ok", "message": "Recommendation approved and executed", **result}
    
    else:
        # Just log dismissal
        logger.info(f"[advisory] User {current_user.id} DISMISSED advisory for zone {payload.zone_id}")
        return {"status": "ok", "message": "Recommendation dismissed"}

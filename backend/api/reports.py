"""
API Router — Reports & Advisory
GET /reports
GET /diary
GET /advisory/{zone_id}
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone, timedelta

from backend.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.models.user import User
from backend.models.farm import Farm, Zone
from backend.models.state import FarmDiaryEntry
from backend.models.decision import DecisionLog
from backend.services.water_usage import compute_water_used
from backend.services.advisory import simplify_advisory
from backend.core.state.state_manager import state_manager
from typing import Dict, Any
from backend.services.diary_builder import diary_builder
from pydantic import BaseModel
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reports & Advisory"])

class ActivityLog(BaseModel):
    zone_id: uuid.UUID
    activity_type: str # "fertilizer" | "harvest"
    title: str
    body: str
    metadata: Dict[str, Any]
    is_subsidy: bool = True

@router.post("/activity")
async def log_farm_activity(
    activity: ActivityLog,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log manual farmer activities (fertilizer, harvest) for subsidy tracking."""
    # Find active farm for user
    farm_result = await db.execute(
        select(Farm.id).where(Farm.user_id == current_user.id)
    )
    farm_id = farm_result.scalars().first()
    if not farm_id:
        raise HTTPException(404, "No farm found.")

    entry = await diary_builder.log_activity(
        farm_id=str(farm_id),
        zone_id=str(activity.zone_id),
        activity_type=activity.activity_type,
        title=activity.title,
        body=activity.body,
        metadata=activity.metadata,
        db=db,
        is_subsidy=activity.is_subsidy
    )
    await db.commit()
    return {"status": "success", "entry_id": str(entry.id)}


@router.get("/diary")
async def get_diary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    farm_result = await db.execute(
        select(Farm.id).where(Farm.user_id == current_user.id)
    )
    farm_id = farm_result.scalars().first()
    if not farm_id:
        raise HTTPException(404, "No farm found.")

    result = await db.execute(
        select(FarmDiaryEntry).where(FarmDiaryEntry.farm_id == farm_id)
        .order_by(desc(FarmDiaryEntry.created_at)).limit(limit)
    )
    entries = result.scalars().all()
    return {"entries": [
        {
            "id": str(e.id), "zone_id": str(e.zone_id) if e.zone_id else None, 
            "timestamp": e.created_at,
            "type": e.entry_type, "title": e.title, "description": e.body,
            "is_subsidy_relevant": e.is_subsidy_relevant,
            "subsidy_status": e.subsidy_status,
            "payment_reference": e.payment_reference,
            "cost": float(e.cost or 0.0),
            "record_data": e.record_data
        } for e in entries
    ]}


@router.get("/water-usage")
async def get_water_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    farm_result = await db.execute(
        select(Farm).where(Farm.user_id == current_user.id)
    )
    farm = farm_result.scalar_one_or_none()
    if not farm:
        raise HTTPException(404, "No farm found.")

    # Get zones for farm
    zones_result = await db.execute(select(Zone.id).where(Zone.farm_id == farm.id))
    zone_ids = [z for z in zones_result.scalars().all()]

    if not zone_ids:
        return {"recent_irrigation_count": 0, "total_duration_min": 0, "water_used_liters": 0, "water_used_per_acre": 0}

    # Get decisions that were irrigate
    dec_result = await db.execute(
        select(DecisionLog).where(
            DecisionLog.zone_id.in_(zone_ids), 
            DecisionLog.decision == "irrigate"
        ).order_by(desc(DecisionLog.time)).limit(50)
    )
    decisions = dec_result.scalars().all()
    
    total_minutes = sum(d.duration_min or 0 for d in decisions)
    usage = compute_water_used(total_minutes, area_acres=farm.total_acres or 1.0)
    
    return {
        "recent_irrigation_count": len(decisions),
        "total_duration_min": total_minutes,
        "water_used_liters": usage["total_liters"],
        "water_used_per_acre": usage["per_acre_liters"]
    }


@router.get("/advisory/{zone_id}")
async def get_zone_advisory(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates simple single-sentence advisory for a zone."""
    state = state_manager.get_cached_zone_context(zone_id)
    if not state:
        raise HTTPException(404, "Zone state not found.")

    zone_result = await db.execute(select(Zone).where(Zone.id == zone_id))
    zone = zone_result.scalar_one_or_none()

    advisory = await simplify_advisory(
        decision=state.get("last_decision", "skip"),
        duration_min=state.get("last_irrigation_duration_min", 0),
        stage=state.get("current_stage", "Unknown"),
        moisture_now=state.get("current_moisture", 0.0) or 0.0,
        moisture_target=state.get("target_moisture_min", 0.0) or 0.0,
        rain_prob_6h=state.get("rain_prob_6h", 0.0) or 0.0,
        confidence=0.8,
        zone_name=zone.name if zone else f"Zone {zone_id}",
        lang=current_user.preferred_lang,
    )
    return {"advisory": advisory}
@router.get("/sensors/history")
async def get_sensor_history(
    zone_id: uuid.UUID,
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch historical sensor readings for a zone."""
    # 1. Verify zone belongs to user's farm
    res = await db.execute(
        select(Zone).join(Farm).where(Zone.id == zone_id, Farm.user_id == current_user.id)
    )
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    # 2. Fetch readings
    from backend.models.sensor_data import SensorReading
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await db.execute(
        select(SensorReading).where(SensorReading.zone_id == zone_id, SensorReading.time >= start_date)
        .order_by(SensorReading.time)
    )
    readings = result.scalars().all()
    
    return [
        {
            "time": r.time,
            "soil_moisture": r.soil_moisture,
            "temperature": r.temperature,
            "humidity": r.humidity,
        } for r in readings
    ]

@router.post("/reports/send")
async def send_report_to_gov(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Simulate sending a PDF report to a government agency email."""
    report_id = payload.get("report_id")
    email = payload.get("email")
    
    if not report_id or not email:
        raise HTTPException(status_code=400, detail="Missing report_id or email")
        
    logger.info(f"[reports] Sending report {report_id} to {email} for user {current_user.id}")
    return {"status": "success", "message": f"Report sent to {email}"}

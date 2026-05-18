"""
API Router — Crop Planning
POST /planner
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid
import logging

logger = logging.getLogger(__name__)

from backend.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.models.user import User
from backend.models.farm import Farm, Zone
from backend.plugins.ai.planner.crop_planner import plan_crop
from backend.services.weather import get_weather

router = APIRouter(prefix="/planner", tags=["Crop Planner"])

class PlannerRequest(BaseModel):
    zone_id: str
    current_season: Optional[str] = "current"
    farmer_goal: Optional[str] = "maximize_yield"
    query: Optional[str] = "Provide a growth strategy."
    budget_inr_per_acre: Optional[float] = None
    mode: str = "new_season" # "new_season" or "existing_crop"
    lang: Optional[str] = None


@router.post("")
async def generate_crop_plan(
    payload: PlannerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch farm & zone
    farm_result = await db.execute(
        select(Farm).where(Farm.user_id == current_user.id)
    )
    farm = farm_result.scalar_one_or_none()
    if not farm:
        raise HTTPException(404, "No active farm found.")

    zone_result = await db.execute(
        select(Zone).where(Zone.id == payload.zone_id, Zone.farm_id == farm.id)
    )
    zone = zone_result.scalar_one_or_none()
    if not zone:
        raise HTTPException(404, "Zone not found.")

    # Convert to dicts for prompt
    farm_dict = {"name": farm.name, "location": farm.location, "acres": farm.total_acres, "soil": zone.soil_type}
    zone_dict = {
        "name": zone.name, 
        "acres": zone.area_acres, 
        "irrigation_method": zone.irrigation_type,
        "current_crop": zone.crop_type
    }

    weather = {}
    if farm.latitude and farm.longitude:
        weather = await get_weather(farm.latitude, farm.longitude, lang=current_user.preferred_lang)

    lang = payload.lang or current_user.preferred_lang

    result = await plan_crop(
        farm=farm_dict,
        zone=zone_dict,
        current_season=payload.current_season,
        farmer_goal=payload.farmer_goal,
        weather_30d=weather,
        query=payload.query,
        lang=lang,
        budget_inr_per_acre=payload.budget_inr_per_acre,
        mode=payload.mode
    )

    if result.get("status") == "failed":
        raise HTTPException(500, result.get("error"))

    # PERSISTENCE PILLAR: Save the plan to DB
    from backend.models.decision import CropPlan
    import json
    
    new_plan = CropPlan(
        id=uuid.uuid4(),
        zone_id=payload.zone_id,
        farm_id=farm.id,
        crop_name=result.get("recommended_crop", "Unknown"),
        season=result.get("season", payload.current_season),
        weekly_plan=result.get("weekly_plan"),
        fertilizer_schedule=result.get("fertilizer_schedule"),
        irrigation_plan=result.get("irrigation_plan"),
    )
    db.add(new_plan)
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"[planner] Failed to save plan: {e}")

    return result

@router.post("/generate/{zone_id}")
async def generate_zone_plan(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Simple zone-level plan generation wrapper."""
    # We'll use defaults for season and goal as the frontend call is minimalist
    payload = PlannerRequest(
        zone_id=zone_id,
        current_season="current",
        farmer_goal="maximize_yield",
        query="Provide a growth strategy for this zone."
    )
    return await generate_crop_plan(payload, db, current_user)
@router.get("/{zone_id}")
async def get_latest_plan(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch the latest saved plan for a zone."""
    from backend.models.decision import CropPlan
    from sqlalchemy import desc
    
    res = await db.execute(
        select(CropPlan).where(CropPlan.zone_id == zone_id)
        .order_by(desc(CropPlan.created_at)).limit(1)
    )
    plan = res.scalar_one_or_none()
    if not plan:
        return {"status": "none", "message": "No plans found for this zone."}

    return {
        "status": "success",
        "recommended_crop": plan.crop_name,
        "season": plan.season,
        "weekly_plan": plan.weekly_plan,
        "fertilizer_schedule": plan.fertilizer_schedule,
        "irrigation_plan": plan.irrigation_plan,
        "created_at": plan.created_at
    }

@router.get("/crops")
async def list_crops():
    """Return a list of supported crops for the planner."""
    return ["Tomato", "Sugarcane", "Chilli", "Cotton", "Maize", "Coffee"]

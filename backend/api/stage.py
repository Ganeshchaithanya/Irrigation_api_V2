"""
API Router — Stage Awareness
GET /stage
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from backend.plugins.ai.stage.stage_model import predict_stage

router = APIRouter(prefix="/stage", tags=["Stage API"])

@router.get("")
async def get_crop_stage(
    crop: str = Query(..., description="Crop name (e.g. Rice, Maize)"),
    day: int = Query(..., description="Days after planting"),
    moisture: Optional[float] = Query(None, description="Current soil moisture %"),
    season: str = Query("kharif", description="Season (kharif, rabi, zaid)"),
):
    """
    Get current growth stage and metadata for a crop.
    Incorporates biological delay if moisture is too low.
    """
    # Use 50.0 as default moisture if not provided to avoid triggering correction
    current_moisture = moisture if moisture is not None else 100.0
    
    result = predict_stage(
        crop=crop,
        season=season,
        days_after_planting=day,
        soil_moisture_avg_24h=current_moisture
    )
    
    return result

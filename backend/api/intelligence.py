from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any
from backend.services.intelligence import generate_growth_stages, get_predefined_crops, get_predefined_crop_data

router = APIRouter(prefix="/intelligence", tags=["Agricultural Intelligence"])

@router.get("/crops", response_model=List[str])
async def list_crops():
    """Get list of supported crops from predefined database."""
    return get_predefined_crops()

@router.get("/crop-config")
async def get_crop_config(crop: str = Query(..., description="Crop name")):
    """
    Get full growth stage and configuration data for a crop.
    Checks predefined database first, then falls back to AI generation.
    """
    # 1. Check predefined
    data = get_predefined_crop_data(crop)
    if data:
        return {
            "source": "database",
            "crop_name": data["name"],
            "crop_category": data.get("category", "Unknown"),
            "growth_stages": data["growth_stages"]
        }
    
    # 2. Fallback to AI
    ai_data = await generate_growth_stages(crop)
    if "error" in ai_data:
        raise HTTPException(status_code=500, detail=ai_data["error"])
    
    return {
        "source": "ai_engine",
        "crop_name": ai_data.get("crop_name", crop),
        "crop_category": ai_data.get("crop_category", "Unknown"),
        "growth_stages": ai_data.get("growth_stages", [])
    }

@router.get("/setup-hints")
async def get_setup_hints(crop: str = Query(..., description="Crop name")):
    """
    Provides all dynamic data needed for the Farm Setup UI.
    Includes stages, week ranges, and smart defaults.
    """
    data = get_predefined_crop_data(crop)
    source = "database"
    
    if not data:
        data = await generate_growth_stages(crop)
        source = "ai_engine"
        if "error" in data:
            raise HTTPException(status_code=500, detail=data["error"])

    # Extract stages with week info
    stages = []
    for s in data.get("growth_stages", []):
        stages.append({
            "name": s.get("stage") or s.get("name"),
            "week_start": s.get("week_start", s.get("days_start", 0) // 7),
            "week_end": s.get("week_end", s.get("days_end", 0) // 7),
            "moisture_min": s.get("soil_moisture_min", 50),
            "moisture_max": s.get("soil_moisture_max", 70),
            "explanation": s.get("explanation", "")
        })

    # Suggest season based on current month if not predefined
    import datetime
    month = datetime.datetime.now().month
    suggested_season = "kharif" if 6 <= month <= 10 else "rabi" if (month >= 11 or month <= 2) else "zaid"

    return {
        "crop": crop,
        "source": source,
        "suggested_season": suggested_season,
        "stages": stages,
        "defaults": {
            "irrigation_type": "drip",
            "morning_window": "05:00-09:00",
            "evening_window": "18:00-22:00"
        }
    }

@router.get("/generate-stages")
async def get_generated_stages(crop: str = Query(..., description="Crop name")):
    """Force AI generation of growth stages for a crop."""
    ai_data = await generate_growth_stages(crop)
    if "error" in ai_data:
        raise HTTPException(status_code=500, detail=ai_data["error"])
    return ai_data

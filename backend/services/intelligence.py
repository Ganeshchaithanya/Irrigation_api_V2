import json
import re
from typing import List, Dict, Any, Optional
from groq import Groq
from backend.config.settings import get_settings
from backend.utils.logger import logger
import os

settings = get_settings()

_groq_client = None

def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    try:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        return _groq_client
    except Exception as e:
        logger.error(f"[intelligence] Groq client init failed: {e}")
        return None

_STAGE_GEN_PROMPT = """You are an agricultural intelligence system. Given a crop name, generate accurate, scientifically valid growth stages specific to that crop.

Instructions:
1. Identify the crop category (cereal, fruit, vegetable, root, legume, etc.).
2. Use established agricultural standards such as BBCH or Zadoks scale where applicable.
3. Generate only the relevant growth stages for that crop—do NOT force generic stages like "flowering" or "fruiting" if they are not biologically applicable.
4. Ensure stages reflect real agronomic importance (e.g., tillering in cereals, tuber formation in potatoes, bolting in leafy crops).
5. Keep the stages in correct chronological order.
6. Use concise, domain-accurate terminology.
7. For each stage, estimate a duration in DAYS from the start of the previous stage (or from sowing for the first stage). Total duration should be realistic.

Output format MUST be valid JSON:
{{
  "crop_name": "...",
  "crop_category": "...",
  "growth_stages": [
    {{
      "stage": "Stage Name",
      "explanation": "Short explanation",
      "days_duration": 10,
      "soil_moisture_min": 50,
      "soil_moisture_max": 70
    }},
    ...
  ]
}}
"""

async def generate_growth_stages(crop: str) -> Dict[str, Any]:
    """Generates growth stages using Groq AI."""
    client = _get_groq_client()
    if not client:
        return {"error": "AI client not available"}

    try:
        response = client.chat.completions.create(
            model=getattr(settings, "GROQ_CHAT_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": _STAGE_GEN_PROMPT},
                {"role": "user", "content": f"Input: {crop}"}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        
        # Calculate cumulative days
        current_day = 0
        for stage in data.get("growth_stages", []):
            stage["days_start"] = current_day
            current_day += stage.get("days_duration", 10)
            stage["days_end"] = current_day
            # Estimate week range for UI
            stage["week_start"] = stage["days_start"] // 7
            stage["week_end"] = stage["days_end"] // 7
            
        return data
    except Exception as e:
        logger.error(f"[intelligence] Failed to generate stages for {crop}: {e}")
        return {"error": str(e)}

def get_predefined_crops() -> List[str]:
    """Returns a list of unique crop names from the JSON data files."""
    crops = set()
    data_dir = settings.DATA_DIR
    for season in ["kharif", "rabi", "zaid"]:
        path = os.path.join(data_dir, f"{season}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for c in data.get("crops", []):
                        crops.add(c["name"])
            except:
                pass
    return sorted(list(crops))

def get_predefined_crop_data(crop_name: str) -> Optional[Dict[str, Any]]:
    """Returns data for a crop if it exists in JSON files."""
    data_dir = settings.DATA_DIR
    for season in ["kharif", "rabi", "zaid"]:
        path = os.path.join(data_dir, f"{season}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for c in data.get("crops", []):
                        if c["name"].lower() == crop_name.lower():
                            # Add week info
                            for stage in c.get("growth_stages", []):
                                stage["week_start"] = stage["days_start"] // 7
                                stage["week_end"] = stage["days_end"] // 7
                            return c
            except:
                pass
    return None

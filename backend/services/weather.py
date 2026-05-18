"""
Service — Weather
Fetches weather + rain probability from OpenWeatherMap API.
"""
import httpx
import time
from typing import Dict, Any, Optional
from backend.config.settings import get_settings
from backend.utils.logger import logger

settings = get_settings()

# Simple In-Memory Cache
_weather_cache = {}
CACHE_TTL = 1800 # 30 minutes

async def get_weather(lat: float, lon: float, lang: str = "en") -> Dict[str, Any]:
    """Fetch current weather + 6h/24h rain probability with 30m cache."""
    cache_key = f"{round(lat, 2)}_{round(lon, 2)}"
    now = time.time()
    
    if cache_key in _weather_cache:
        data, ts = _weather_cache[cache_key]
        if now - ts < CACHE_TTL:
            return data
            
    try:
        url = f"{settings.WEATHER_BASE_URL}/weather/forecast"
        params = {
            "lat": lat, "lon": lon,
            "appid": settings.WEATHER_API_KEY,
            "lang": lang
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            forecasts = resp.json()

        if not isinstance(forecasts, list):
            forecasts = []
        rain_prob_6h = _max_rain_prob(forecasts[:2])
        rain_prob_24h = _max_rain_prob(forecasts[:8])
        
        # Extract rain volume (mm) for next 6h
        rain_mm_6h = sum([f.get("rain", {}).get("3h", 0.0) for f in forecasts[:2]])
        
        current = forecasts[0] if forecasts else {}

        result = {
            "temperature": current.get("main", {}).get("temp"),
            "humidity": current.get("main", {}).get("humidity"),
            "condition": current.get("weather", [{}])[0].get("main", "Sunny"),
            "description": current.get("weather", [{}])[0].get("description", ""),
            "rain_prob_6h": round(rain_prob_6h, 3),
            "rain_prob_24h": round(rain_prob_24h, 3),
            "rain_mm_6h": round(rain_mm_6h, 2),
            "wind_speed": current.get("wind", {}).get("speed"),
            "status": "ok",
        }
        _weather_cache[cache_key] = (result, now)
        return result
    except Exception as e:
        logger.warning(f"[weather] API error: {e}")
        return {"rain_prob_6h": 0.1, "rain_prob_24h": 0.2, "status": "error", "error": str(e)}


def _max_rain_prob(forecasts: list) -> float:
    probs = [f.get("pop", 0.0) for f in forecasts]
    return max(probs) if probs else 0.0

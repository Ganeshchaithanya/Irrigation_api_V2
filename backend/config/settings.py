"""
AquaSol — Central settings loaded from .env
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
import os


class Settings(BaseSettings):
    # ── Project ──────────────────────────────────────────────────────────
    PROJECT_NAME: str = "AquaSol Irrigation API"
    VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(..., validation_alias="DATABASE_URL")

    # ── Auth ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(default="changeme-in-production", validation_alias="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ── Groq (Whisper only — kept for voice transcription) ──────────────────
    GROQ_API_KEY: str = Field(..., validation_alias="GROQ_API_KEY")
    GROQ_CHAT_MODEL: str = "llama-3.3-70b-versatile"   # legacy, use HF for planning
    GROQ_WHISPER_MODEL: str = "whisper-large-v3-turbo"

    # ── HuggingFace Inference API (Planner + Chatbot Brain) ──────────────────
    HF_API_TOKEN: str = Field(default="", validation_alias="HF_API_TOKEN")
    HF_CHAT_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.3"

    # ── Weather ───────────────────────────────────────────────────────────
    WEATHER_API_KEY: str = Field(..., validation_alias="WEATHER_API_KEY")
    WEATHER_BASE_URL: str = "http://api.agromonitoring.com/agro/1.0"

    # ── LEGACY MQTT (Decommissioned) ────────────────────────────────────
    MQTT_BROKER_HOST: str = Field(default="localhost", validation_alias="MQTT_BROKER_HOST")
    MQTT_BROKER_PORT: int = Field(default=1883, validation_alias="MQTT_BROKER_PORT")
    MQTT_USERNAME: str = Field(default="", validation_alias="MQTT_USERNAME")
    MQTT_PASSWORD: str = Field(default="", validation_alias="MQTT_PASSWORD")
    MQTT_ENABLED: bool = Field(default=False, validation_alias="MQTT_ENABLED")

    # ── ML Model paths ────────────────────────────────────────────────────
    MODELS_DIR: str = Field(
        default=os.path.join(os.path.dirname(__file__), "..", "models_store"),
        validation_alias="MODELS_DIR"
    )
    DATA_DIR: str = Field(
        default=os.path.join(os.path.dirname(__file__), "..", "data"),
        validation_alias="DATA_DIR"
    )

    # ── E5 (Memory / RAG) ────────────────────────────────────────────────
    E5_MODEL_NAME: str = "intfloat/multilingual-e5-large"

    # ── Trust Engine ─────────────────────────────────────────────────────
    TRUST_THRESHOLD: float = 0.5         # below → virtual sensing
    VIRTUAL_SENSING_PEERS_MIN: int = 2   # min peers to compute zone mean

    # ── Decision Physics — Calibration ──────────────────────────────────
    # Soil Water Holding Factor (mm/mm)
    SOIL_HOLD_FACTOR: dict = {
        "sandy": 0.1,
        "sandy_loam": 0.15,
        "clay_loam": 0.22,
        "loam": 0.18,
        "clay": 0.25
    }

    # Soil-Adaptive Soak Times (Minutes between cycles)
    SOIL_SOAK_TIME: dict = {
        "sandy": 15,
        "sandy_loam": 25,
        "clay_loam": 40,
        "loam": 30,
        "clay": 60
    }

    # Crop-Stage Root Depths (Maize focus)
    STAGE_ROOT_DEPTH: dict = {
        "early": 250,
        "vegetative": 500,
        "flowering": 800,
        "fruit_development": 500,
        "default": 300
    }

    # ── Field Biochemistry / Agronomy (Finesse) ─────────────────────────
    CROP_SENSITIVITY_PROFILES: dict = {
        "tomato": {
            "sensitive_stages": ["fruit_development", "fruiting"], 
            "max_recovery_mm": 8.5, 
            "always_sensitive": False,
            "kc": {"early": 0.6, "vegetative": 0.85, "flowering": 1.15, "fruiting": 1.1, "fruit_development": 1.05, "default": 0.8}
        },
        "peanut": {
            "sensitive_stages": ["flowering", "pegging"], 
            "max_recovery_mm": 7.0, 
            "always_sensitive": False,
            "kc": {"early": 0.4, "vegetative": 0.8, "flowering": 1.15, "pegging": 1.1, "default": 0.8}
        },
        "pepper": {
            "sensitive_stages": ["flowering", "fruiting"], 
            "max_recovery_mm": 9.0, 
            "always_sensitive": False,
            "kc": {"early": 0.6, "vegetative": 0.85, "flowering": 1.15, "fruiting": 1.0, "default": 0.8}
        },
        "lettuce": {
            "sensitive_stages": ["all"], 
            "max_recovery_mm": 6.0, 
            "always_sensitive": True,
            "kc": {"early": 0.7, "vegetative": 1.0, "harvest": 0.95, "default": 0.9}
        },
        "maize": {
            "sensitive_stages": ["flowering", "silking"], 
            "max_recovery_mm": 15.0, 
            "always_sensitive": False,
            "kc": {"early": 0.3, "vegetative": 0.8, "flowering": 1.2, "silking": 1.2, "harvest": 0.5, "default": 0.8}
        },
        "rice": {
            "sensitive_stages": [], 
            "max_recovery_mm": 20.0, 
            "always_sensitive": False,
            "kc": {"early": 1.05, "vegetative": 1.2, "flowering": 1.2, "harvest": 0.9, "default": 1.1}
        }, 
        "default": {
            "sensitive_stages": [], 
            "max_recovery_mm": 12.0, 
            "always_sensitive": False,
            "kc": {"default": 1.0}
        }
    }

    # Hardware Thresholds
    DEFAULT_APP_RATE_MM_HR: float = 2.0
    DEFAULT_IRRIGATION_EFFICIENCY: float = 0.9  # Drip default
    MAX_MM_PER_CYCLE: float = 6.0
    RAIN_IGNORE_THRESHOLD_MM: float = 8.0  # Ignore rain < 8mm
    
    # ── Safety & Abortion Logic ──────────────────────────────────────────
    ABORT_SPIKE_THRESHOLD_PCT: float = 3.0
    EMERGENCY_STOP_COOLDOWN_HOURS: float = 12.0
    
    # ── Anomaly Detection (Hydraulic Continuity) ──────────────────────────
    # Max physically possible moisture drop per hour (% points)
    # Beyond this → Sensor Drift suspected
    MAX_MOISTURE_DROP_PCT_PER_HOUR: dict = {
        "sandy": 5.0,
        "sandy_loam": 4.0,
        "loam": 3.0,
        "clay_loam": 2.5,
        "clay": 2.0,
        "default": 3.5
    }
    DRIFT_PENALTY_TRUST_SCORE: float = 0.1
    
    # ── Perception Intelligence (Slow Drift & Reasoning) ──────────────────
    SLOW_DRIFT_THRESHOLD_PCT: float = 8.0  # Deviation from 24h rolling avg
    IRRIGATION_RESPONSE_TOLERANCE_PCT: float = 0.3 # 30% of expected gain
    TRUST_RECOVERY_RATE: float = 0.05      # +5% trust per stable cycle
    CORRELATION_THRESHOLD_PCT: float = 12.0 # Deviation between peer zones


    # ── Trust & Calibration ─────────────────────────────────────────────
    MIN_MODEL_CONFIDENCE: float = 0.5
    MAX_MODEL_CONFIDENCE: float = 0.9      # Cap to avoid "Dangerous Illusion"
    TRUST_CALIBRATION_FACTOR: float = 1.0

    # ── Policy Enforcement Thresholds ─────────────────────────────────────
    RECENT_IRRIGATION_HOURS: int = 4
    MAX_IRRIGATION_DURATION_MIN: int = 90
    BATTERY_CRITICAL_PCT: float = 15.0
    EMERGENCY_MOISTURE_DEFICIT: float = 20.0
    
    # ── SLA Guardrails ──────────────────────────────────────────────────
    ABSOLUTE_MAX_MOISTURE: float = 90.0 # Extreme flood warning
    MAX_MM_PER_24H: float = 20.0 # Safety limit to stop infinite loops

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

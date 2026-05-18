"""
Pydantic Schemas — Dashboard & Zone responses
"""
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


class NodeStatus(BaseModel):
    node_label: str
    mac_address: Optional[str]
    status: str
    trust_score: float
    is_virtual: bool
    last_seen: Optional[datetime]
    battery_pct: Optional[float]
    current_moisture: Optional[float] = None
    temperature: Optional[float] = None

    class Config:
        from_attributes = True


class MasterGatewayData(BaseModel):
    device_id: Any
    mac_address: Optional[str]
    last_seen: Optional[datetime]
    flow_rate: float = 0.0
    total_water: float = 0.0
    rain_detected: bool = False
    battery_pct: float = 0.0
    solar_voltage: float = 0.0
    solar_pct: float = 0.0
    status: str = "active"


class ZoneStateResponse(BaseModel):
    zone_id: Any
    name: str
    crop_type: Optional[str]
    season: Optional[str]
    current_stage: Optional[str]
    days_after_planting: int

    current_moisture: Optional[float]
    estimated_root_moisture: Optional[float]
    operating_mode: Optional[str] = "active"
    moisture_trend: float
    predicted_moisture_1h: Optional[float]
    predicted_moisture_6h: Optional[float]
    predicted_moisture_24h: Optional[float]
    target_moisture_min: float
    target_moisture_max: float
    moisture_deficit: float

    temperature_avg_6h: Optional[float]
    humidity_avg_6h: Optional[float]
    rain_prob_6h: Optional[float]

    valve_state: bool
    trust_score_avg: float
    virtual_sensing_active: bool
    master_battery_pct: Optional[float]

    last_decision: Optional[str]
    last_decision_at: Optional[datetime]
    last_irrigation_at: Optional[datetime]
    last_irrigation_duration_min: Optional[int]

    active_alerts: List[Any]
    nodes: List[NodeStatus]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class AcreStateResponse(BaseModel):
    acre_id: Any
    name: str
    total_zones: int
    active_zones: int
    current_moisture_avg: Optional[float]
    zones: List[ZoneStateResponse]

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    farm_id: Any
    name: str
    total_acres: int
    total_zones: int
    active_zones: int
    acres: List[AcreStateResponse]
    zones: List[ZoneStateResponse] # Keep for compatibility
    weather: Optional[Dict[str, Any]]
    master_status: Optional[MasterGatewayData] = None
    metrics: Dict[str, Any] = {
        "water_used_today": 0,
        "ai_decisions_count": 0,
        "health_score": 90,
        "advisory": None
    }
    total_alerts: int
    updated_at: datetime


class DecisionResponse(BaseModel):
    zone_id: Any
    action: str
    duration_min: int
    target_moisture: Optional[float]
    confidence: Optional[float]
    policy_applied: Optional[str]
    policy_reason: Optional[str]
    feature_importance: Optional[Dict[str, float]]
    stage: Optional[str]

    class Config:
        from_attributes = True


class OverrideRequest(BaseModel):
    zone_id: Any
    node_slot_id: Optional[Any] = None
    action: str           # irrigate | stop
    duration_min: int = 15
    reason: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    lang: str = "en"      # en | kn | hi | te
    voice_mode: bool = False


class ChatResponse(BaseModel):
    reply: str
    lang: str
    audio_url: Optional[str] = None   # path to TTS audio file


class ZonePatchRequest(BaseModel):
    mode: Optional[str] = None # manual | auto
    operating_mode: Optional[str] = None # active | shadow


class ScheduleCreate(BaseModel):
    label: Optional[str] = None
    zone_id: Optional[Any] = None
    acre_id: Optional[Any] = None
    time: str
    days: List[str]
    duration_min: int = 30
    intensity: int = 80
    mode: str = "manual"
    is_active: bool = True


class AcreOverrideRequest(BaseModel):
    acre_id: Any
    action: str           # irrigate | stop
    duration_min: int = 15
    reason: Optional[str] = None

class AdvisoryActionRequest(BaseModel):
    zone_id: Any
    action: str           # approve | dismiss
    decision_id: Optional[str] = None

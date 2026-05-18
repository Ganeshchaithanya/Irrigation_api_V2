"""
Pydantic Schemas — Sensor Ingestion (ESP32 payload)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime, timezone


class SensorEvent(BaseModel):
    """Single telemetry event from a node."""
    node_mac: str = Field(..., alias="nodeMac")
    pairing_code: Optional[str] = Field(None, alias="pairingCode")
    soil_moisture: float = Field(..., alias="soilMoisture")
    temperature: Optional[float] = Field(None, alias="temperature")
    humidity: Optional[float] = Field(None, alias="humidity")
    valve_status: int = Field(0, alias="valveStatus")
    battery_pct: Optional[float] = Field(None, alias="batteryPct")
    solar_pct: Optional[float] = Field(None, alias="solarPct")

    model_config = ConfigDict(populate_by_name=True)

class SensorBatch(BaseModel):
    """Batch of telemetry events from a master node (Flat structure)."""
    master_mac: str = Field(..., alias="masterMac")
    pairing_code: Optional[str] = Field(None, alias="pairingCode")
    battery_pct: Optional[float] = Field(None, alias="batteryPct")
    solar_pct: Optional[float] = Field(None, alias="solarPct")
    solar_voltage: Optional[float] = Field(None, alias="solarVoltage")
    rain_detected: int = Field(0, alias="rainDetected")
    flow_rate: Optional[float] = Field(None, alias="flowRate")
    total_water: Optional[float] = Field(None, alias="totalWater")
    events: List[SensorEvent] = Field(..., alias="events")

    model_config = ConfigDict(populate_by_name=True)

class TelemetryResponse(BaseModel):
    """Response returned to the master node after ingestion."""
    status: str = "success"
    processed_count: int
    commands: List[dict] = []
    # Simplified node commands: { "MAC": bool }
    node_targets: Dict[str, bool] = {} 
    virtual_sensing_active: bool = False
    failed_nodes: List[str] = []
    message: Optional[str] = None

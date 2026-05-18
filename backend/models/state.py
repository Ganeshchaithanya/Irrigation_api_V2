import uuid
from sqlalchemy import Column, String, Numeric, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from backend.db.base import Base

class ZoneState(Base):
    """Maps to 'zone_state' table (current live state per zone)."""
    __tablename__ = "zone_state"
    
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), primary_key=True)
    current_moisture = Column(Numeric(5, 2))
    predicted_moisture_1h = Column(Numeric(5, 2))
    predicted_moisture_6h = Column(Numeric(5, 2))
    predicted_moisture_24h = Column(Numeric(5, 2))
    target_moisture_min = Column(Numeric(5, 2))
    target_moisture_max = Column(Numeric(5, 2))
    
    current_stage = Column(String)
    stage_confidence = Column(Numeric(4, 3))
    days_after_planting = Column(Integer)
    
    last_irrigation_at = Column(DateTime(timezone=True))
    last_irrigation_duration = Column(Integer)
    valve_state = Column(String, nullable=False, default="closed")
    moisture_at_irrigation_start = Column(Numeric(5, 2)) # Safety baseline
    
    weather_rain_prob_6h = Column(Numeric(5, 2))
    weather_temp = Column(Numeric(5, 2))
    
    ai_recommendation = Column(String)
    model_confidence = Column(Numeric(4, 3))
    uncertainty_flag = Column(String)
    
    # Perception & Calibration
    rolling_avg_24h = Column(Numeric(5, 2))
    moisture_at_irrigation_end = Column(Numeric(5, 2))
    expected_gain_mm = Column(Numeric(5, 2))
    execution_confidence = Column(Numeric(4, 3))
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class FarmDiaryEntry(Base):
    """Maps to 'diary_entries' table."""
    __tablename__ = "diary_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=False)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"))
    
    entry_type = Column(String, nullable=False)
    source = Column(String, nullable=False, default="auto")
    title = Column(String)
    body = Column(String)
    
    # New fields for Subsidy & Rich Logging
    is_subsidy_relevant = Column(Boolean, default=False)
    subsidy_status = Column(String) # "pending", "approved", "paid"
    cost = Column(Numeric(10, 2), default=0.0)
    payment_status = Column(String, default="unpaid") # "unpaid", "paid", "reimbursed"
    payment_reference = Column(String)
    record_data = Column(String) # JSON string for fertilizer/harvest details
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

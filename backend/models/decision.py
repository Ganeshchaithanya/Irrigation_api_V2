import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from backend.db.base import Base

class ValveCommand(Base):
    """Maps to 'valve_commands' table."""
    __tablename__ = "valve_commands"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    node_slot_id = Column(UUID(as_uuid=True), ForeignKey("node_slots.id"), nullable=True)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=False)
    
    source = Column(String, nullable=False) # 'ai', 'manual'
    state = Column(String, nullable=False)  # 'open', 'closed'
    duration_min = Column(Integer)
    mqtt_topic = Column(String, nullable=True) # Legacy - now optional
    payload = Column(JSONB, nullable=False)
    
    status = Column(String, nullable=False, default="pending")
    
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    received_at = Column(DateTime(timezone=True)) # Stage 1 Confirmation
    acked_at = Column(DateTime(timezone=True))    # Stage 2 Confirmation
    closed_at = Column(DateTime(timezone=True))
    actual_duration_min = Column(Integer)
    notes = Column(String)


class DecisionLog(Base):
    """Maps to 'decision_log' table."""
    __tablename__ = "decision_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    
    decision = Column(String, nullable=False) # 'irrigate', 'skip', 'delay'
    duration_min = Column(Integer)
    
    # Physics-Aware Metrics (mm-first)
    water_required_mm = Column(Numeric(5, 2))
    cycles = Column(Integer, default=1)
    
    confidence = Column(Numeric(4, 3))
    policy_blocked = Column(Boolean, default=False)
    block_reason = Column(String)
    feature_snapshot = Column(JSONB)
    top_factors = Column(JSONB) # Explainability feature importances
    ood_flag = Column(Boolean, default=False) # Out-Of-Distribution flag
    explanation = Column(String)


class CropPlan(Base):
    """Maps to 'crop_plans' table."""
    __tablename__ = "crop_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=False)
    crop_name = Column(String, nullable=False)
    season = Column(String, nullable=False)
    
    weekly_plan = Column(JSONB)
    fertilizer_schedule = Column(JSONB)
    irrigation_plan = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Schedule(Base):
    """Maps to 'schedules' table for both AI windows and manual timers."""
    __tablename__ = "schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=True)
    acre_id = Column(UUID(as_uuid=True), ForeignKey("acres.id", ondelete="CASCADE"), nullable=True)
    
    label = Column(String) # e.g. "Morning Pulse"
    time = Column(String, nullable=False) # "06:00"
    days = Column(JSONB, nullable=False) # ["Mon", "Wed", "Fri"]
    duration_min = Column(Integer, default=30)
    intensity = Column(Integer, default=80) # % of max flow
    
    mode = Column(String, default="manual") # 'auto' (AI window) or 'manual' (timer)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

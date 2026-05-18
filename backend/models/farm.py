import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Date, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.db.base import Base

class Farm(Base):
    __tablename__ = "farms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    location = Column(String)
    latitude = Column(Numeric)
    longitude = Column(Numeric)
    total_acres = Column(Integer, default=1)
    zones_per_acre = Column(Integer, default=4)
    water_source = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    zones = relationship("Zone", back_populates="farm", cascade="all, delete-orphan")
    acres_list = relationship("Acre", back_populates="farm", cascade="all, delete-orphan")


class Acre(Base):
    __tablename__ = "acres"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    size = Column(Numeric(10, 2), default=1.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    farm = relationship("Farm", back_populates="acres_list")
    zones = relationship("Zone", back_populates="acre")


class Zone(Base):
    __tablename__ = "zones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False)
    acre_id = Column(UUID(as_uuid=True), ForeignKey("acres.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    
    # Restored from production schema
    crop_type = Column(String)
    season = Column(String) # e.g. 'kharif', 'rabi', 'zaid'
    soil_type = Column(String) # e.g. 'Clay', 'Sandy', 'Loam'
    mode = Column(String(10), default="auto") # manual/auto
    operating_mode = Column(String(50), default="active") # active/shadow
    
    area_acres = Column(Numeric(6, 2))
    sowing_date = Column(Date)
    current_stage = Column(String) # early, vegetative, flowering, etc.
    expected_harvest = Column(Date)
    
    morning_window = Column(String) # e.g. "05:00-09:00"
    evening_window = Column(String) # e.g. "18:00-22:00"
    
    min_moisture_threshold = Column(Numeric(5, 2), default=15.0)
    max_moisture_threshold = Column(Numeric(5, 2), default=85.0)
    max_irrigation_duration_sec = Column(Integer, default=3600)
    # Spatial Reasoning
    sensor_depth_cm = Column(Integer, default=10)
    root_depth_cm = Column(Integer, default=30)
    
    # Physics-Aware Calibration (mm-first)
    application_rate_mm_hr = Column(Numeric(5, 2), default=2.0)
    efficiency = Column(Numeric(3, 2), default=0.90) # 0.0 to 1.0
    irrigation_type = Column(String, default="drip") # 'drip' or 'sprinkler'
    
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    farm = relationship("Farm", back_populates="zones")
    acre = relationship("Acre", back_populates="zones")
    node_slots = relationship("NodeSlot", back_populates="zone", cascade="all, delete-orphan")


class NodeSlot(Base):
    """
    Logical irrigation position (e.g. Node1, Node2).
    A NodeSlot belongs to a Zone and can be occupied by a physical Device.
    """
    __tablename__ = "node_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False) # e.g. "Node1"

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    zone = relationship("Zone", back_populates="node_slots")
    # The relationship to Device will be defined in Device model

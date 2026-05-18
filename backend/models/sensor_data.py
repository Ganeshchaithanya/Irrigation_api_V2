from sqlalchemy import Column, String, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.db.base import Base

class SensorReading(Base):
    """Maps to TimescaleDB 'sensor_readings' hypertable."""
    __tablename__ = "sensor_readings"
    
    time = Column(DateTime(timezone=True), primary_key=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), primary_key=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=True)
    node_slot_id = Column(UUID(as_uuid=True), ForeignKey("node_slots.id"), nullable=True)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=False)
    
    # Node sensors
    soil_moisture = Column(Numeric(5, 2))
    temperature = Column(Numeric(5, 2))
    humidity = Column(Numeric(5, 2))
    valve_status = Column(Boolean, default=False)
    
    # Master sensors
    flow_rate = Column(Numeric(8, 3))
    total_water = Column(Numeric(10, 3))
    rain_detected = Column(Boolean)
    battery_pct = Column(Numeric(5, 2))
    solar_pct = Column(Numeric(5, 2))
    solar_voltage = Column(Numeric(5, 2))
    
    # Meta
    is_virtual = Column(Boolean, nullable=False, default=False)
    raw_payload = Column(JSONB)

import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from backend.db.base import Base

class PairingSession(Base):
    """Temporary table for short-lived IoT pairing codes."""
    __tablename__ = "pairing_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mac_address = Column(String(17), nullable=True) # Will be filled when device appears
    pairing_code = Column(String(8), unique=True, nullable=False)
    farm_id = Column(UUID(as_uuid=True), nullable=False)
    zone_id = Column(UUID(as_uuid=True), nullable=True)
    node_slot_id = Column(UUID(as_uuid=True), nullable=True)
    is_master = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

import uuid
from sqlalchemy import Column, String, Boolean, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.db.base import Base

class Device(Base):
    """Replaces 'Node'. Maps to 'devices' table."""
    __tablename__ = "devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), nullable=True)
    node_slot_id = Column(UUID(as_uuid=True), ForeignKey("node_slots.id"), nullable=True)
    
    device_uid = Column(String, unique=True, nullable=False)
    pairing_code = Column(String, unique=True, nullable=True)
    device_secret = Column(String, nullable=True) # Secure token issued after pairing
    mac_address = Column(String, unique=True, nullable=True)
    
    is_master = Column(Boolean, nullable=False, default=False)
    role = Column(String, nullable=False, default="node") # master | node
    is_claimed = Column(Boolean, nullable=False, default=False)
    
    node_label = Column(String)
    firmware_version = Column(String)
    last_seen_at = Column(DateTime(timezone=True))
    bound_at = Column(DateTime(timezone=True))
    status = Column(String, nullable=False, default="active")
    trust_score = Column(Numeric(4, 3), nullable=False, default=1.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    node_slot = relationship("NodeSlot")

import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func
from backend.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String, nullable=True) # Matches screenshot
    auth_provider = Column(String, nullable=True)   # Matches screenshot
    preferred_lang = Column(String, nullable=False, default="en")
    avatar_url = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_admin  = Column(Boolean, nullable=False, default=False)  # Company staff only
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

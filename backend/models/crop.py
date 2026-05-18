import uuid
from sqlalchemy import Column, String, Numeric, Boolean, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from backend.db.base import Base

class CropBioProfile(Base):
    __tablename__ = "crop_bio_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    
    season = Column(String, default="kharif")
    duration_days = Column(Integer, default=120)
    water_req_mm = Column(Integer, default=500)
    osmotic_shock_sensitive = Column(Boolean, default=False)
    rrc_max_mm_per_cycle = Column(Numeric(5, 2), default=12.0)
    
    # Store tuples or lists representing the split e.g. [0.60, 0.40]
    rrc_stage_split = Column(JSONB, default=lambda: [0.5, 0.5])
    
    temp_stress_threshold_c = Column(Numeric(5, 2), default=35.0)
    temp_optimal_min_c = Column(Numeric(5, 2), default=20.0)
    temp_optimal_max_c = Column(Numeric(5, 2), default=30.0)
    tsi_threshold = Column(Numeric(5, 2), default=45.0)
    
    # Example: {"initial": 0.60, "development": 0.90, "mid": 1.15, "late": 0.80, "harvest": 0.60}
    kc_json = Column(JSONB, nullable=False)
    
    # Example: [{"name": "Seedling", "start": 0, "end": 25, "min_m": 55, "max_m": 65}, ...]
    stages_json = Column(JSONB, nullable=False)
    
    soil_type = Column(String, default="loamy")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

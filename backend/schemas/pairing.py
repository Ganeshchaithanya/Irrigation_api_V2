from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class PairingInitiateRequest(BaseModel):
    mac_address: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
    firmware_ver: Optional[str] = None

class PairingInitiateResponse(BaseModel):
    pairing_code: str
    expires_in: int = 120 # Seconds

class PairingClaimRequest(BaseModel):
    pairing_code: str
    farm_id: UUID
    zone_id: Optional[UUID] = None
    node_slot_id: Optional[UUID] = None
    node_name: Optional[str] = None
    is_master: bool = False

class PairingClaimResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    mac: Optional[str] = None
    device_id: Optional[str] = None
    device_secret: Optional[str] = None # Only returned once during pairing

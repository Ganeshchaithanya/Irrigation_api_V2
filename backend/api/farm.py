from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import uuid

from backend.db.session import get_db
from backend.models.farm import Farm, Zone, Acre, NodeSlot
from backend.models.device import Device
from backend.utils.logger import logger
from backend.utils.security import generate_pairing_code

router = APIRouter(prefix="/farms", tags=["Farm Management"])

# --- Schemas ---

class FarmCreate(BaseModel):
    name: str
    location: Optional[str] = None
    total_acres: Optional[int] = 1
    zones_per_acre: Optional[int] = 4
    water_source: Optional[str] = None

class NodeCreate(BaseModel):
    uid: Optional[str] = None
    label: str
    mac: Optional[str] = None # App might send it, but we ignore it during setup

class ZoneCreate(BaseModel):
    farm_id: uuid.UUID
    acre_id: Optional[uuid.UUID] = None
    name: str
    crop_type: str
    season: Optional[str] = None
    soil_type: str
    area_acres: Optional[float] = 1.0
    sowing_date: Optional[str] = None
    irrigation_type: Optional[str] = "drip"
    min_moisture_threshold: Optional[float] = 15.0
    max_moisture_threshold: Optional[float] = 85.0
    morning_window: Optional[str] = "05:00-09:00"
    evening_window: Optional[str] = "18:00-22:00"
    weeks_since_sowing: Optional[int] = 0
    current_stage: Optional[str] = None
    node_slots_count: Optional[int] = 0
    nodes: List[NodeCreate] = []

# --- Endpoints ---

from backend.app.dependencies import get_current_user, get_current_user_from_request
from backend.models.user import User

from fastapi import Body

@router.post("/farm", status_code=status.HTTP_201_CREATED)
async def create_farm(
    payload: FarmCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new farm for a user with auto-named acres."""
    user_id = current_user.id
    
    farm = Farm(
        id=uuid.uuid4(),
        user_id=user_id,
        name=payload.name,
        location=payload.location,
        total_acres=payload.total_acres,
        zones_per_acre=payload.zones_per_acre,
        water_source=payload.water_source,
    )
    db.add(farm)
    await db.flush() 
    
    # Create auto-named Acres
    acres = []
    num_acres = payload.total_acres or 1
    for i in range(1, num_acres + 1):
        acre = Acre(
            id=uuid.uuid4(),
            farm_id=farm.id,
            name=f"Acre {i}",
            size=1.0
        )
        db.add(acre)
        acres.append(acre)
    
    await db.flush()
    
    try:
        await db.commit()
        return {
            "status": "success", 
            "id": str(farm.id), 
            "name": farm.name,
            "acres": [{"id": str(a.id), "name": a.name} for a in acres]
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"[farm] Failed to create farm: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@router.post("/zone", status_code=status.HTTP_201_CREATED)
async def create_zone(
    payload: ZoneCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new zone. Nodes are linked later via /assign."""
    farm_res = await db.execute(select(Farm).where(Farm.id == payload.farm_id, Farm.user_id == current_user.id))
    if not farm_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    zone = Zone(
        id=uuid.uuid4(),
        farm_id=payload.farm_id,
        acre_id=payload.acre_id,
        name=payload.name,
        crop_type=payload.crop_type,
        season=payload.season or "kharif",
        soil_type=payload.soil_type,
        area_acres=payload.area_acres,
        current_stage=payload.current_stage or "early",
        irrigation_type=payload.irrigation_type,
        status="active"
    )
    db.add(zone)
    await db.flush()

    # Create NodeSlots
    slots = []
    for i in range(1, (payload.node_slots_count or 0) + 1):
        slot = NodeSlot(
            id=uuid.uuid4(),
            zone_id=zone.id,
            name=f"Node {i}"
        )
        db.add(slot)
        slots.append(slot)

    try:
        await db.commit()
        return {
            "status": "success", 
            "id": str(zone.id), 
            "name": zone.name,
            "node_slots": [{"id": str(s.id), "name": s.name} for s in slots]
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database Error")

@router.get("/{farm_id}/acres")
async def get_farm_acres(farm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Acre).where(Acre.farm_id == farm_id).order_by(Acre.name))
    acres = res.scalars().all()
    return [{"id": str(a.id), "name": a.name} for a in acres]

@router.get("/acre/{acre_id}/zones")
async def get_acre_zones(acre_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Zone).where(Zone.acre_id == acre_id).order_by(Zone.name))
    zones = res.scalars().all()
    return [{"id": str(z.id), "name": z.name} for z in zones]

@router.post("/node_slot", status_code=status.HTTP_201_CREATED)
async def create_node_slot(
    zone_id: uuid.UUID = Body(..., embed=True),
    name: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a single node slot to a zone."""
    slot = NodeSlot(
        id=uuid.uuid4(),
        zone_id=zone_id,
        name=name
    )
    db.add(slot)
    try:
        await db.commit()
        return {"status": "success", "id": str(slot.id), "name": slot.name}
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, "Database Error")

@router.delete("/node_slot/{slot_id}")
async def delete_node_slot(
    slot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a node slot (unlinks any assigned device)."""
    res = await db.execute(select(NodeSlot).where(NodeSlot.id == slot_id))
    slot = res.scalar_one_or_none()
    if not slot:
        raise HTTPException(404, "Slot not found")
        
    # Unlink device if any
    await db.execute(
        Device.__table__.update()
        .where(Device.node_slot_id == slot_id)
        .values(node_slot_id=None, is_claimed=False)
    )
    
    await db.delete(slot)
    await db.commit()
    return {"status": "success"}

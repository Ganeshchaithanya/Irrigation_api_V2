from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from datetime import datetime, timezone, timedelta
import traceback
import secrets
import uuid

from backend.db.session import get_db
from backend.models.device import Device
from backend.models.farm import Farm, Zone, Acre, NodeSlot
from backend.api.auth import get_current_user
from backend.models.user import User
from backend.utils.logger import logger

router = APIRouter(tags=["Device Management"])

# ─── Schemas ───────────────────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    mac: str
    pairing_code: str
    role: str = "node" # master | node

class AssignRequest(BaseModel):
    pairing_code: str
    farm_id: str
    acre_id: str
    zone_id: str
    node_slot_id: str

# ─── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/discover")
async def discover_device(payload: DiscoverRequest, db: AsyncSession = Depends(get_db)):
    """Device-side: Hardware announces itself on boot with pairing code."""
    try:
        res = await db.execute(select(Device).where(Device.mac_address == payload.mac))
        device = res.scalar_one_or_none()
        
        if not device:
            device = Device(
                id=uuid.uuid4(),
                device_uid="DEV-" + payload.mac.replace(":", "")[-6:],
                mac_address=payload.mac,
                pairing_code=payload.pairing_code.upper(),
                role=payload.role,
                is_master=(payload.role == "master"),
                status="discovery",
                is_claimed=False,
                last_seen_at=datetime.now(timezone.utc)
            )
            db.add(device)
        else:
            device.last_seen_at = datetime.now(timezone.utc)
            # Update pairing code if it changed (e.g. re-flashed)
            device.pairing_code = payload.pairing_code.upper()
            
        await db.commit()
        return {"status": "ok", "is_claimed": device.is_claimed}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/unassigned")
async def get_unassigned_devices(db: AsyncSession = Depends(get_db)):
    """App-side: List devices waiting for assignment (Discovery mode)."""
    # Show devices seen in the last 2 hours that aren't bound to a farm
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    res = await db.execute(
        select(Device).where(
            Device.farm_id == None,
            Device.last_seen_at > cutoff
        ).order_by(Device.last_seen_at.desc())
    )
    devices = res.scalars().all()
    return [{
        "id": str(d.id),
        "device_id": d.device_uid,
        "mac": d.mac_address,
        "is_master": d.is_master,
        "last_seen": d.last_seen_at.isoformat() if d.last_seen_at else None,
        "label": d.node_label or ("Master Gateway" if d.is_master else "Node")
    } for d in devices]

@router.post("/assign")
async def assign_device(
    payload: AssignRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """App-side: Bind a physical Device to a logical NodeSlot using pairing code."""
    try:
        # 1. Resolve Device by Pairing Code
        res = await db.execute(select(Device).where(Device.pairing_code == payload.pairing_code.upper()))
        device = res.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail="Invalid pairing code. Device not discovered.")
            
        if device.is_claimed:
            raise HTTPException(status_code=400, detail="Device is already claimed by another slot.")

        # 2. Validate IDs
        def safe_uuid(id_str: str) -> uuid.UUID:
            try: return uuid.UUID(id_str)
            except: raise HTTPException(status_code=400, detail=f"Invalid UUID: {id_str}")

        farm_id = safe_uuid(payload.farm_id)
        node_slot_id = safe_uuid(payload.node_slot_id)

        # 3. Bind Device to NodeSlot
        device.farm_id = farm_id
        device.node_slot_id = node_slot_id
        device.is_claimed = True
        device.status = "active"
        device.bound_at = datetime.now(timezone.utc)
        
        # Issue a secret if it's the first time
        if not device.device_secret:
            device.device_secret = secrets.token_urlsafe(32)

        await db.commit()
        return {
            "status": "success", 
            "mac": device.mac_address,
            "role": device.role
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"[assign] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during assignment")

@router.get("/config")
async def get_device_config(mac: str, db: AsyncSession = Depends(get_db)):
    """Master-side: Fetch the logical topology and MAC mappings for the farm."""
    try:
        # 1. Resolve Master
        res = await db.execute(select(Device).where(Device.mac_address == mac, Device.is_master == True))
        master = res.scalar_one_or_none()
        if not master or not master.farm_id:
            raise HTTPException(status_code=404, detail="Master unknown or unassigned")

        # 2. Fetch all node slots and their bound devices for this farm
        # In a real scenario, you might filter by Acre/Zone if the Master only covers some
        res = await db.execute(
            select(NodeSlot, Device.mac_address)
            .join(Device, Device.node_slot_id == NodeSlot.id, isouter=True)
            .join(Zone, NodeSlot.zone_id == Zone.id)
            .where(Zone.farm_id == master.farm_id)
        )
        slots = res.all()

        config = {
            "config_version": datetime.now(timezone.utc).isoformat(),
            "farm_id": str(master.farm_id),
            "nodes": []
        }

        for slot, node_mac in slots:
            config["nodes"].append({
                "slot_name": slot.name,
                "node_mac": node_mac,
                "slot_id": str(slot.id)
            })

        return config
    except Exception as e:
        logger.error(f"[config] Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch configuration")

@router.get("/system-health")
async def get_system_health(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Device))
    devices = res.scalars().all()
    nodes = []
    online_count = 0
    total_score = 0
    for d in devices:
        is_online = False
        if d.last_seen_at:
            delta = (datetime.now(timezone.utc) - d.last_seen_at).total_seconds()
            if delta < 300:
                is_online = True
                online_count += 1
        nodes.append({
            "label": d.node_label or f"Node {d.device_uid[:4]}",
            "status": "online" if is_online else "offline",
            "last_seen": d.last_seen_at
        })
        score = 100 if is_online else 20
        total_score += score
    avg_score = int(total_score / len(devices)) if devices else 100
    return {
        "score": avg_score,
        "total_nodes": len(devices),
        "online_nodes": online_count,
        "nodes": nodes
    }

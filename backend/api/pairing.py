import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from backend.db.session import get_db
from backend.models.pairing_session import PairingSession
from backend.models.device import Device
from backend.models.user import User
from backend.api.auth import get_current_user
from backend.schemas.pairing import (
    PairingInitiateRequest, PairingInitiateResponse,
    PairingClaimRequest, PairingClaimResponse
)
from backend.utils.logger import logger

router = APIRouter(tags=["Pairing"])

@router.post("/assign/code")
async def claim_code(
    payload: PairingClaimRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User registers a code. The backend will bind the next device that sends this code."""
    # 1. Clean up any existing sessions for this code
    await db.execute(
        delete(PairingSession).where(
            PairingSession.pairing_code == payload.pairing_code.upper()
        )
    )
    
    # 2. Create the claim reservation
    session = PairingSession(
        pairing_code=payload.pairing_code.upper(),
        farm_id=payload.farm_id,
        zone_id=payload.zone_id,
        node_slot_id=payload.node_slot_id if hasattr(payload, 'node_slot_id') else None,
        is_master=payload.is_master if hasattr(payload, 'is_master') else (payload.zone_id is None),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    db.add(session)
    
    # 3. Check if a device with this code already exists in discovery mode
    dev_res = await db.execute(
        select(Device).where(
            Device.pairing_code == payload.pairing_code.upper()
        )
    )
    existing_dev = dev_res.scalar_one_or_none()
    
    if existing_dev:
        logger.info(f"[pairing] Instant-pairing discovered device {existing_dev.mac_address} to farm {payload.farm_id}")
        existing_dev.farm_id = payload.farm_id
        existing_dev.node_slot_id = payload.node_slot_id
        existing_dev.status = "active"
        existing_dev.is_claimed = True
        existing_dev.node_label = payload.node_name or ("Main Controller" if existing_dev.is_master else "Acre Node")
        session.is_used = True
        session.device_id = existing_dev.id
        
        await db.commit()
        return {
            "status": "success", 
            "message": "Hardware linked successfully!",
            "mac": existing_dev.mac_address,
            "device_id": str(existing_dev.id)
        }

    try:
        await db.commit()
        return {"status": "success", "message": "Waiting for device to connect..."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register claim")

"""
AquaSol Admin API
=================
Company-internal endpoints for hardware management.

SECURITY:  These endpoints require a valid JWT token from an account where
           is_admin = True.  Only admin@aquasol.com (and any other accounts
           explicitly promoted in the DB) can call these routes.

           Login normally via POST /api/v1/auth/login with admin@aquasol.com
           and use the returned access_token as:  Authorization: Bearer <token>
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.models.device import Device
from backend.models.user import User
from backend.app.dependencies import get_current_user
from backend.utils.logger import logger

router = APIRouter(prefix="/admin", tags=["AquaSol Admin"])


# ─── Admin Guard ───────────────────────────────────────────────────────────────

async def _require_admin(current_user: User = Depends(get_current_user)):
    """
    Dependency: validates that the JWT belongs to an is_admin=True account.
    Only admin@aquasol.com (or any other DB-promoted account) passes.
    All other users receive 403 Forbidden.
    """
    if not getattr(current_user, 'is_admin', False):
        logger.warning(f"[admin] Rejected: user {current_user.email} attempted admin access.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. This account is not authorised for hardware management."
        )
    return current_user


# ─── Schemas ───────────────────────────────────────────────────────────────────

class DeviceReplaceRequest(BaseModel):
    """
    Body for POST /admin/devices/replace

    old_pairing_code:  The pairing code of the FAULTY device to be retired.
    new_pairing_code:  The pairing code of the REPLACEMENT device (already
                       in discovery mode — it must have called /discover first).
    reason:            Short description of the failure (for audit trail).
                       e.g. "Moisture sensor burnt, approved by ticket #AQ-1042"
    technician:        Name/ID of the AquaSol staff member authorising the swap.
    """
    old_pairing_code: str
    new_pairing_code: str
    reason: str
    technician: str


class DeviceReleaseRequest(BaseModel):
    """
    Body for POST /admin/devices/release

    Completely unclaims a device (sets is_claimed=False, clears farm_id).
    Use this ONLY when decommissioning hardware permanently.
    """
    pairing_code: str
    reason: str
    technician: str


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/devices/replace", dependencies=[Depends(_require_admin)])
async def replace_device(
    payload: DeviceReplaceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Company-approved hardware swap.

    Transfers the permanent farm/slot binding from the faulty device to a
    replacement device.  The old device is marked 'replaced' and its
    is_claimed flag is cleared so it can no longer send telemetry.

    Requirements:
    - Old device must currently be claimed (is_claimed=True).
    - New device must exist in the DB (it called /discover at least once).
    - New device must NOT already be claimed by a different farm.
    """
    old_code = payload.old_pairing_code.upper().strip()
    new_code = payload.new_pairing_code.upper().strip()

    # 1. Fetch the faulty device
    old_res = await db.execute(select(Device).where(Device.pairing_code == old_code))
    old_dev = old_res.scalar_one_or_none()

    if not old_dev:
        raise HTTPException(status_code=404, detail=f"Faulty device with code '{old_code}' not found.")
    if not old_dev.is_claimed:
        raise HTTPException(status_code=400, detail="Device is not currently claimed — nothing to replace.")

    # 2. Fetch the replacement device
    new_res = await db.execute(select(Device).where(Device.pairing_code == new_code))
    new_dev = new_res.scalar_one_or_none()

    if not new_dev:
        raise HTTPException(
            status_code=404,
            detail=f"Replacement device '{new_code}' not found. Ensure the new hardware has booted and called /discover."
        )
    if new_dev.is_claimed and str(new_dev.farm_id) != str(old_dev.farm_id):
        raise HTTPException(
            status_code=409,
            detail="Replacement device is already claimed by a different farm. Cannot transfer."
        )

    # 3. Transfer binding: copy all logical assignments from old → new
    new_dev.farm_id      = old_dev.farm_id
    new_dev.node_slot_id = old_dev.node_slot_id
    new_dev.is_claimed   = True
    new_dev.status       = "active"
    new_dev.is_master    = old_dev.is_master
    new_dev.role         = old_dev.role
    new_dev.node_label   = old_dev.node_label
    new_dev.bound_at     = datetime.now(timezone.utc)

    # 4. Retire the old device — mark replaced, clear claim so it can't send data
    old_dev.is_claimed   = False
    old_dev.status       = "replaced"
    old_dev.farm_id      = None
    old_dev.node_slot_id = None

    await db.commit()

    logger.info(
        f"[admin] Device REPLACED: old={old_code} ({old_dev.mac_address}) → "
        f"new={new_code} ({new_dev.mac_address}) | "
        f"technician={payload.technician} | reason={payload.reason}"
    )

    return {
        "status": "success",
        "message": f"Device '{old_code}' has been retired. '{new_code}' is now permanently assigned.",
        "old_device": {
            "pairing_code": old_code,
            "mac_address": old_dev.mac_address,
            "status": "replaced"
        },
        "new_device": {
            "pairing_code": new_code,
            "mac_address": new_dev.mac_address,
            "farm_id": str(new_dev.farm_id),
            "status": "active"
        },
        "technician": payload.technician,
        "reason": payload.reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/devices/release", dependencies=[Depends(_require_admin)])
async def release_device(
    payload: DeviceReleaseRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently decommission a device (e.g. hardware is physically destroyed).
    Clears is_claimed and farm binding so the slot is freed.
    """
    code = payload.pairing_code.upper().strip()
    res = await db.execute(select(Device).where(Device.pairing_code == code))
    dev = res.scalar_one_or_none()

    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{code}' not found.")

    dev.is_claimed   = False
    dev.status       = "decommissioned"
    dev.farm_id      = None
    dev.node_slot_id = None
    await db.commit()

    logger.warning(
        f"[admin] Device DECOMMISSIONED: code={code} mac={dev.mac_address} | "
        f"technician={payload.technician} | reason={payload.reason}"
    )

    return {
        "status": "success",
        "message": f"Device '{code}' has been decommissioned.",
        "technician": payload.technician,
        "reason": payload.reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/devices/list", dependencies=[Depends(_require_admin)])
async def list_all_devices(db: AsyncSession = Depends(get_db)):
    """List all devices in the system with their current claim status."""
    res = await db.execute(select(Device).order_by(Device.created_at.desc()))
    devices = res.scalars().all()
    return [{
        "pairing_code":  d.pairing_code,
        "mac_address":   d.mac_address,
        "device_uid":    d.device_uid,
        "is_claimed":    d.is_claimed,
        "is_master":     d.is_master,
        "status":        d.status,
        "farm_id":       str(d.farm_id) if d.farm_id else None,
        "node_label":    d.node_label,
        "last_seen_at":  d.last_seen_at.isoformat() if d.last_seen_at else None,
    } for d in devices]

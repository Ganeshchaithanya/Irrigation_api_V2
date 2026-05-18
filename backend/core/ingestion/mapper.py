"""
Core Ingestion — Mapper
Resolves MAC address → (node_id, zone_id, farm_id) from the database.
Creates new Device records for unregistered MACs under the correct farm.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from backend.models.device import Device
from backend.models.farm import Farm, Zone
from backend.core.ingestion.parser import ParsedNodeEvent
from backend.utils.logger import logger


async def resolve_node(
    event: ParsedNodeEvent,
    farm_id: str,
    db: AsyncSession,
) -> Optional[Device]:
    """
    Look up or auto-create a Device record for a given MAC.
    Returns None if farm has no zones (misconfigured).
    """
    result = await db.execute(
        select(Device).where(Device.mac_address == event.mac_address)
    )
    device = result.scalar_one_or_none()

    if device:
        # Update node metadata
        from datetime import datetime, timezone
        device.last_seen_at = datetime.now(timezone.utc)
        device.is_master = event.is_master
        await db.flush()
        return device

    # Auto-register: assign to first active zone of the farm
    zone_result = await db.execute(
        select(Zone).where(Zone.farm_id == farm_id, Zone.status == "active").limit(1)
    )
    zone = zone_result.scalar_one_or_none()
    if not zone:
        logger.warning(f"[mapper] No zone found for farm_id={farm_id}. Cannot register device {event.mac_address}")
        return None

    from datetime import datetime, timezone
    new_device = Device(
        farm_id=farm_id,
        zone_id=zone.id,
        node_label=event.node_label,
        mac_address=event.mac_address,
        is_master=event.is_master,
        status="active",
        last_seen_at=datetime.now(timezone.utc),
        trust_score=1.0,
    )
    db.add(new_device)
    await db.flush()
    logger.info(f"[mapper] Auto-registered new device {event.mac_address} → zone {zone.name}")
    return new_device


async def get_farm_by_api_key(api_key: str, db: AsyncSession) -> Optional[Farm]:
    """
    Resolves a Farm instance using an API key.
    Currently, the Farm UUID is used directly as the API Key for hardware telemetry.
    """
    result = await db.execute(
        select(Farm).where(Farm.id == api_key)
    )
    return result.scalar_one_or_none()

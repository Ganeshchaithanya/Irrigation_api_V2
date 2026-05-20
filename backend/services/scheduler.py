import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.db.session import engine
from backend.models.device import Device
from backend.models.farm import NodeSlot
from backend.services.alerts import create_alert
from backend.utils.logger import logger

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession)

async def check_device_health():
    """Background task to monitor device heartbeats and trigger offline alerts."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Find devices that have been claimed and have a node slot
                result = await db.execute(
                    select(Device, NodeSlot.zone_id)
                    .join(NodeSlot, Device.node_slot_id == NodeSlot.id)
                    .where(Device.is_claimed == True)
                )
                devices = result.all()
                
                now = datetime.now(timezone.utc)
                for device, zone_id in devices:
                    is_offline = False
                    if not device.last_seen_at:
                        # If bound more than 5 mins ago but never seen
                        if device.bound_at and (now - device.bound_at.replace(tzinfo=timezone.utc)).total_seconds() > 300:
                            is_offline = True
                    else:
                        if (now - device.last_seen_at.replace(tzinfo=timezone.utc)).total_seconds() > 300:
                            is_offline = True
                            
                    if is_offline and device.status != "failed":
                        logger.warning(f"[scheduler] Node {device.node_label or device.mac_address} went OFFLINE.")
                        device.status = "failed"
                        device.trust_score = 0.0
                        
                        await create_alert(
                            farm_id=str(device.farm_id),
                            zone_id=str(zone_id),
                            alert_type="node_failure",
                            title="📡 Node Offline Alert",
                            description=f"Device {device.node_label or device.mac_address} has not sent telemetry in over 5 minutes. System failing over to Virtual Sensing.",
                            db=db
                        )
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"[scheduler] Error in health check loop: {e}")
            
        await asyncio.sleep(60) # Check every 60 seconds

def start_scheduler():
    asyncio.create_task(check_device_health())

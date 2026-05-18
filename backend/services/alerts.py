"""
Service — Alert Management
Generates, stores and retrieves alerts for anomalies, node failures, moisture warnings.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.models.state import FarmDiaryEntry
from backend.utils.logger import logger

ALERT_TYPES = {
    "anomaly": "🔴 Sensor Anomaly",
    "low_moisture": "💧 Low Moisture",
    "high_moisture": "🌊 High Moisture",
    "node_failure": "📡 Node Offline",
    "battery_low": "🔋 Battery Critical",
    "irrigation_complete": "✅ Irrigation Done",
    "stage_change": "🌱 Stage Changed",
    "virtual_sensing": "⚡ Virtual Sensing Active",
}


async def create_alert(
    farm_id: str,
    zone_id: Optional[str],
    alert_type: str,
    title: str,
    description: str,
    db: AsyncSession,
    metadata: Optional[Dict] = None,
):
    """Persist an alert as a FarmDiaryEntry."""
    entry = FarmDiaryEntry(
        farm_id=farm_id,
        zone_id=zone_id,
        entry_type=alert_type,
        title=title,
        body=description,
    )
    db.add(entry)
    await db.flush()
    logger.info(f"[alerts] [{alert_type}] {title}")
    return entry


async def get_recent_alerts(
    farm_id: str,
    db: AsyncSession,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(FarmDiaryEntry)
        .where(FarmDiaryEntry.farm_id == farm_id)
        .order_by(desc(FarmDiaryEntry.created_at))
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "type": r.entry_type,
            "title": r.title,
            "description": r.body,
            "zone_id": str(r.zone_id) if r.zone_id else None,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
            "metadata": {},
        }
        for r in rows
    ]


def build_anomaly_alert(node_label: str, sensor: str, value: float,
                         anomaly_type: str, is_virtual: bool) -> Dict[str, str]:
    """Build alert payload for sensor anomaly."""
    virtual_note = " (virtual sensing activated)" if is_virtual else ""
    return {
        "title": f"Unusual reading on Node {node_label}",
        "description": (
            f"Node {node_label} shows an unexpected {sensor} value of {value:.1f}% "
            f"(type: {anomaly_type}){virtual_note}. "
            f"Please check if the sensor is damaged or submerged."
        ),
    }

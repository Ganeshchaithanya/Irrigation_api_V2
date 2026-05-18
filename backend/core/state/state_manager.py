"""
Core — State Manager
Central in-memory + DB-persisted real-time state for all zones.
All AI modules read from state, never from raw DB.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.models.state import ZoneState
from backend.models.farm import Zone
from backend.utils.logger import logger

# In-memory state cache: { zone_id: dict }
_state_cache: Dict[str, Dict[str, Any]] = {}
# Heartbeat cache: { node_mac: datetime }
_node_heartbeats: Dict[str, datetime] = {}


class StateManager:
    """Singleton-style state manager. Instantiate once in startup."""

    async def get_zone_state(self, zone_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        if zone_id in _state_cache:
            return _state_cache[zone_id]
        return await self._load_from_db(zone_id, db)

    async def update_zone_state(self, zone_id: str, updates: Dict[str, Any], db: AsyncSession):
        """Update both memory cache and DB atomically."""
        if zone_id not in _state_cache:
            await self._load_from_db(zone_id, db)

        if zone_id not in _state_cache:
            _state_cache[zone_id] = {}

        _state_cache[zone_id].update(updates)
        _state_cache[zone_id]["updated_at"] = datetime.now(timezone.utc)

        await self._persist_to_db(zone_id, updates, db)

    async def get_all_zone_states(self, farm_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all zone states for a farm (for dashboard)."""
        zones_result = await db.execute(select(Zone.id).where(Zone.farm_id == farm_id))
        zone_ids = [str(zid) for zid in zones_result.scalars().all()]
        
        if not zone_ids:
            return []

        result = await db.execute(
            select(ZoneState).where(ZoneState.zone_id.in_(zone_ids))
        )
        rows = result.scalars().all()
        states = []
        for row in rows:
            state = self._row_to_dict(row)
            _state_cache[str(row.zone_id)] = state
            states.append(state)
        return states

    async def _load_from_db(self, zone_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        result = await db.execute(
            select(ZoneState).where(ZoneState.zone_id == zone_id)
        )
        row = result.scalar_one_or_none()
        if row:
            state = self._row_to_dict(row)
            _state_cache[zone_id] = state
            return state
        return None

    async def _persist_to_db(self, zone_id: str, updates: Dict[str, Any], db: AsyncSession):
        """Upsert zone state into DB."""
        result = await db.execute(
            select(ZoneState).where(ZoneState.zone_id == zone_id)
        )
        row = result.scalar_one_or_none()

        safe_updates = {k: v for k, v in updates.items() if hasattr(ZoneState, k)}

        if row:
            for k, v in safe_updates.items():
                setattr(row, k, v)
            row.updated_at = datetime.now(timezone.utc)
        else:
            new_state = ZoneState(zone_id=zone_id, **safe_updates)
            db.add(new_state)
        await db.flush()

    def _row_to_dict(self, row: ZoneState) -> Dict[str, Any]:
        return {c.name: getattr(row, c.name) for c in row.__table__.columns}

    def get_cached_zone_context(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """Non-async — for chatbot context builder."""
        return _state_cache.get(zone_id)

    def get_all_cached(self) -> Dict[str, Dict[str, Any]]:
        return dict(_state_cache)

    def invalidate(self, zone_id: str):
        _state_cache.pop(zone_id, None)

    def record_heartbeat(self, node_mac: str):
        """Record the last known activity of a sensor node."""
        _node_heartbeats[node_mac] = datetime.now(timezone.utc)

    def get_node_status(self, node_mac: str, ttl_minutes: int = 30) -> str:
        """Check if a node is online or failed based on heartbeat TTL."""
        last_seen = _node_heartbeats.get(node_mac)
        if not last_seen:
            return "unknown"
        
        delta = (datetime.now(timezone.utc) - last_seen).total_seconds() / 60
        return "online" if delta <= ttl_minutes else "failed"


# Singleton instance
state_manager = StateManager()

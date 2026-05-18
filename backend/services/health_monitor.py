"""
Service — Node Health Monitor
Tracks heartbeats and triggers failover / Virtual Sensing.
"""
import asyncio
from datetime import datetime, timezone
from backend.core.state.state_manager import state_manager
from backend.utils.logger import logger
from backend.config.settings import get_settings

settings = get_settings()

class HealthMonitor:
    def __init__(self, ttl_minutes: int = 30):
        self.ttl = ttl_minutes
        self.active_nodes = {} # node_mac -> status
    
    def update_node_freshness(self, node_mac: str):
        """Called whenever telemetry arrives from a node."""
        state_manager.record_heartbeat(node_mac)
        self.active_nodes[node_mac] = "online"

    def get_status(self, node_mac: str) -> str:
        """Returns 'online', 'failed', or 'unknown'."""
        status = state_manager.get_node_status(node_mac, self.ttl)
        # Cache but also update if stale
        self.active_nodes[node_mac] = status
        return status

    async def check_all_health(self):
        """Background task to audit all heartbeats."""
        # Note: state_manager heartbeats are in-memory
        states = state_manager.get_all_cached()
        for zid, state in states.items():
            # Find node Macs associated with this zone? 
            # This would require a DB lookup or cached map.
            # For now, we'll rely on the proactive check in MqttBridge.
            pass

health_monitor = HealthMonitor(ttl_minutes=30)

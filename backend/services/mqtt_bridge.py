"""
RETIRED — MQTT Bridge Service
This component is no longer used. The system has moved to a pure HTTP-based architecture.
All telemetry ingestion now happens via the /api/v1/sensors endpoint.
"""
from backend.utils.logger import logger

class MqttBridge:
    def __init__(self):
        pass

    async def start_listening(self):
        logger.warning("[mqtt-bridge] DEPRECATED: MQTT bridge is no longer used. Listening disabled.")
        pass

mqtt_bridge = MqttBridge()

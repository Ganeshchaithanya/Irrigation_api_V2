"""
Core Ingestion — Parser
Converts raw ESP32 JSON payload → structured sensor events per node.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from backend.schemas.sensor import SensorPayload, NodeReading
from backend.utils.logger import logger


class ParsedNodeEvent:
    """Normalized sensor event from a single node."""
    def __init__(
        self,
        mac_address: str,
        node_label: str,
        is_master: bool,
        soil_moisture: Optional[float],
        temperature: Optional[float],
        humidity: Optional[float],
        rain_detected: bool,
        battery_voltage: Optional[float],
        flow_rate: Optional[float],
        timestamp: datetime,
        farm_api_key: str,
    ):
        self.mac_address = mac_address
        self.node_label = node_label
        self.is_master = is_master
        self.soil_moisture = soil_moisture
        self.temperature = temperature
        self.humidity = humidity
        self.rain_detected = rain_detected
        self.battery_voltage = battery_voltage
        self.flow_rate = flow_rate
        self.timestamp = timestamp
        self.farm_api_key = farm_api_key

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def parse_sensor_payload(payload: SensorPayload) -> List[ParsedNodeEvent]:
    """
    Parse the master node's aggregated payload into individual node events.
    Timestamp defaults to UTC now if not provided.
    """
    ts = payload.timestamp or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    events: List[ParsedNodeEvent] = []

    for node in payload.nodes:
        try:
            event = ParsedNodeEvent(
                mac_address=node.mac_address.upper().strip(),
                node_label=node.node_label.upper().strip(),
                is_master=node.is_master,
                soil_moisture=_clamp(node.soil_moisture, 0.0, 100.0),
                temperature=_clamp(node.temperature, -10.0, 60.0),
                humidity=_clamp(node.humidity, 0.0, 100.0),
                rain_detected=node.rain_detected,
                battery_voltage=_clamp(node.battery_voltage, 0.0, 5.0) if node.battery_voltage else None,
                flow_rate=node.flow_rate,
                timestamp=ts,
                farm_api_key=payload.farm_api_key,
            )
            events.append(event)
        except Exception as e:
            logger.warning(f"[parser] Skipped node {node.node_label}: {e}")

    logger.info(f"[parser] Parsed {len(events)} node events from farm {payload.farm_api_key[:8]}...")
    return events


def _clamp(value: Optional[float], lo: float, hi: float) -> Optional[float]:
    """Clamp a sensor value to physical range. Returns None if input is None."""
    if value is None:
        return None
    return max(lo, min(hi, float(value)))

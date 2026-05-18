"""
Core — Aggregation Engine
Converts node-level readings → zone-level averages → farm-level summary.
"""
from typing import List, Optional, Dict, Any
import statistics
from backend.utils.logger import logger


class ZoneAggregator:
    """Zone-level aggregated sensor data from multiple nodes."""

    def __init__(self, zone_id: Any, zone_name: str = "Unknown"):
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.moisture_values: List[float] = []
        self.temperature_values: List[float] = []
        self.humidity_values: List[float] = []
        self.trust_scores: List[float] = []
        self.rain_detected: bool = False
        self.virtual_sensing_active: bool = False
        self.failed_nodes: int = 0
        self.active_nodes: int = 0

    def add_reading(
        self,
        moisture: Optional[float],
        temperature: Optional[float],
        humidity: Optional[float],
        trust_score: float,
        rain_detected: bool = False,
        is_virtual: bool = False,
    ):
        if moisture is not None:
            self.moisture_values.append(moisture)
        if temperature is not None:
            self.temperature_values.append(temperature)
        if humidity is not None:
            self.humidity_values.append(humidity)
        self.trust_scores.append(trust_score)
        if rain_detected:
            self.rain_detected = True
        if is_virtual:
            self.virtual_sensing_active = True
        self.active_nodes += 1

    def compute(self) -> Dict[str, Any]:
        """Returns zone-level aggregate dict."""
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "soil_moisture_avg": _safe_mean(self.moisture_values),
            "temperature_avg": _safe_mean(self.temperature_values),
            "humidity_avg": _safe_mean(self.humidity_values),
            "trust_score_avg": _safe_mean(self.trust_scores),
            "rain_detected": self.rain_detected,
            "virtual_sensing_active": self.virtual_sensing_active,
            "active_nodes": self.active_nodes,
            "failed_nodes": self.failed_nodes,
            "reading_count": len(self.moisture_values),
        }


class FarmAggregate:
    """Farm-level summary across all zones."""

    def __init__(self, farm_id: int, farm_name: str):
        self.farm_id = farm_id
        self.farm_name = farm_name
        self.zones: List[Dict[str, Any]] = []

    def add_zone(self, zone_agg: Dict[str, Any]):
        self.zones.append(zone_agg)

    def compute(self) -> Dict[str, Any]:
        all_moisture = [z["soil_moisture_avg"] for z in self.zones if z["soil_moisture_avg"] is not None]
        all_trust = [z["trust_score_avg"] for z in self.zones if z["trust_score_avg"] is not None]
        return {
            "farm_id": self.farm_id,
            "farm_name": self.farm_name,
            "zone_count": len(self.zones),
            "avg_farm_moisture": _safe_mean(all_moisture),
            "avg_trust_score": _safe_mean(all_trust),
            "any_rain_detected": any(z["rain_detected"] for z in self.zones),
            "zones": self.zones,
        }


def _safe_mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(statistics.mean(values), 2)

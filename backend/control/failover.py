"""
Control — Failover Logic
When a node fails, peer nodes compensate with adjusted irrigation duration.
"""
from typing import List, Optional
from backend.utils.logger import logger


def compute_failover_duration(
    base_duration_min: float,
    failed_node_area_fraction: float,
    active_peer_count: int,
) -> float:
    """
    Distribute missed coverage of failed node across peers.
    Returns adjusted duration (capped at 1.5x base).
    """
    if active_peer_count == 0:
        return base_duration_min

    extra_per_peer = (failed_node_area_fraction / active_peer_count)
    adjusted = base_duration_min * (1 + extra_per_peer * 0.3)
    capped = min(adjusted, base_duration_min * 1.5)
    logger.info(
        f"[failover] base={base_duration_min:.1f}min "
        f"failed_fraction={failed_node_area_fraction:.2f} "
        f"peers={active_peer_count} → adjusted={capped:.1f}min"
    )
    return round(capped, 1)


def detect_failed_nodes(nodes: List[dict], timeout_minutes: int = 15) -> List[dict]:
    """
    nodes: list of {node_id, last_seen, status, trust_score}
    Returns list of failed nodes.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    failed = []
    for node in nodes:
        last_seen = node.get("last_seen")
        trust = node.get("trust_score", 1.0)
        if last_seen:
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            minutes_silent = (now - last_seen).total_seconds() / 60
            if minutes_silent > timeout_minutes or trust < 0.2:
                failed.append(node)
    return failed

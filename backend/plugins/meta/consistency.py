"""
Meta Plugin — Consistency Engine (v2)
Cross-checks predictions vs stage vs decision for logical coherence.
Also hosts detect_sensor_anomaly() which now delegates to the full
multi-layer anomaly engine in core/reliability/anomaly.py.
"""
from typing import Dict, Any, Optional, List
from backend.utils.logger import logger
from backend.core.reliability.anomaly import detect_anomaly


def check_consistency(
    decision: Dict[str, Any],
    stage_result: Dict[str, Any],
    prediction: Dict[str, Any],
    current_moisture: float,
) -> Dict[str, Any]:
    """
    Validates the decision against stage and predictions.
    Returns { is_consistent, warnings, adjusted_decision }
    """
    warnings = []
    adjusted = dict(decision)

    stage = stage_result.get("stage", "Unknown")
    t_min = stage_result.get("target_moisture_min", 40)
    t_max = stage_result.get("target_moisture_max", 70)
    p6h   = prediction.get("predicted_6h", current_moisture)
    stage_sensitive = stage_result.get("stage_sensitivity", False)  # new v2 field

    # ── Rule 1: Irrigate when already above target_max ────────────────────────
    if decision.get("decision") == "irrigate" and current_moisture >= t_max:
        warnings.append(
            f"Irrigation recommended but moisture ({current_moisture:.1f}%) "
            f"already at/above target_max ({t_max}%)."
        )
        if current_moisture > t_max + 5:
            adjusted["decision"]      = "skip"
            adjusted["duration_min"]  = 0
            adjusted["policy_applied"] = "consistency_override"
            adjusted["policy_reason"] = (
                f"Moisture ({current_moisture:.1f}%) already above target. Override to skip."
            )

    # ── Rule 2: Skip when 6-hour forecast falls critically below target_min ───
    if decision.get("decision") == "skip" and p6h < (t_min - 15):
        warnings.append(
            f"Skip recommended but moisture dropping to {p6h:.1f}% in 6h "
            f"(target_min={t_min}%)."
        )
        adjusted["decision"]    = "delay"
        adjusted["policy_reason"] = (
            "Consistency: 6h forecast critically low — upgrading skip → delay."
        )

    # ── Rule 3: Block irrigation at Harvest stage ─────────────────────────────
    if "harvest" in stage.lower() and decision.get("decision") == "irrigate":
        warnings.append(f"Irrigation blocked — crop in {stage} stage.")
        adjusted["decision"]       = "skip"
        adjusted["duration_min"]   = 0
        adjusted["policy_applied"] = "stage_consistency"
        adjusted["policy_reason"]  = f"No irrigation at {stage} stage."

    # ── Rule 4: Shorten duration on water-sensitive stage (new v2) ───────────
    if (stage_sensitive and decision.get("decision") == "irrigate"
            and (decision.get("duration_min") or 0) > 30):
        original_dur = decision.get("duration_min")
        adjusted["duration_min"] = 30
        warnings.append(
            f"Stage '{stage}' is water-sensitive — duration capped "
            f"{original_dur}→30 min."
        )
        adjusted["policy_reason"] = (
            adjusted.get("policy_reason", "") +
            f" | Sensitive stage cap: {original_dur}→30 min."
        )

    if warnings:
        logger.info(f"[consistency] {len(warnings)} issue(s): {warnings}")

    return {
        "is_consistent": len(warnings) == 0,
        "warnings": warnings,
        "adjusted_decision": adjusted,
    }


def detect_sensor_anomaly(
    current_moisture: float,
    previous_moisture: Optional[float],
    last_updated_at: Optional[Any],
    soil_type: str,
    settings: Any,
    # ── new parameters (v2) ──────────────────────────────────
    temperature: Optional[float] = None,
    humidity: Optional[float] = None,
    zone_id: Optional[str] = None,
    peer_moistures: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Full anomaly check pipeline:
      1. Hydraulic continuity (rate-of-change violation)
      2. Delegates to multi-layer detect_anomaly() for all other patterns

    Returns a result dict compatible with the old { is_anomaly, reason, details }
    but now enriched with severity, anomaly_type, anomaly_score, method, detail.
    """
    # ── Hydraulic continuity (requires time context) ──────────────────────────
    mc_rate = 0.0
    if previous_moisture is not None and last_updated_at is not None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        try:
            time_diff_hours = (now - last_updated_at).total_seconds() / 3600.0
        except TypeError:
            # last_updated_at may be naive — make it timezone-aware
            last_aware = last_updated_at.replace(tzinfo=timezone.utc)
            time_diff_hours = (now - last_aware).total_seconds() / 3600.0

        if time_diff_hours >= 0.1:
            drop = previous_moisture - current_moisture
            mc_rate = -drop / time_diff_hours  # negative = dropping

    # ── Full multi-layer anomaly check ────────────────────────────────────────
    result = detect_anomaly(
        soil_moisture=current_moisture,
        temperature=temperature,
        humidity=humidity,
        moisture_change_rate=mc_rate,
        soil_type=soil_type,
        zone_id=zone_id,
        peer_moistures=peer_moistures,
    )

    return result

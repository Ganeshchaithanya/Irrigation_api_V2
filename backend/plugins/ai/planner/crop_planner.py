"""
AI Plugin — Crop Planner (v2)
Memory = multilingual-e5-large + FAISS semantic search over ICAR crop guides
Brain  = HuggingFace Inference API (Mistral / LLaMA)

Upgrades vs v1:
  - Groq → HuggingFace Inference API
  - FAISS index for O(log n) RAG search at scale
  - Soil-type boosting in RAG retrieval
  - Crop rotation awareness (penalise recently grown crops)
  - Season calendar window (days remaining in season)
  - Structured output validation with schema repair
  - Budget-aware justification field
"""
import os
import re
import json
import math
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime

from backend.config.settings import get_settings
from backend.utils.logger import logger

settings = get_settings()

# ── Optional FAISS import (graceful fallback to numpy cosine) ─────────────────
try:
    import faiss
    _FAISS_AVAILABLE = True
except Exception as e:
    _FAISS_AVAILABLE = False
    logger.warning(f"[planner] FAISS failed to load ({e}) — using numpy cosine search.")

# ── E5 model ──────────────────────────────────────────────────────────────────
try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except Exception as e:
    _ST_AVAILABLE = False
    logger.warning(f"[planner] sentence-transformers failed to load ({e}) — RAG disabled.")

# ── Groq client ──────────────────────────────────────────────────────────────
from groq import Groq
_groq_client: Optional[Groq] = None


# ── State ─────────────────────────────────────────────────────────────────────
_e5_model: Optional[Any] = None
_guide_chunks: List[Dict[str, Any]] = []
_guide_embeddings: Optional[np.ndarray] = None
_faiss_index: Optional[Any] = None     # faiss.IndexFlatIP


# ── Season calendar (approximate) ────────────────────────────────────────────
_SEASON_WINDOWS = {
    "kharif": {"start_month": 6, "end_month": 11},   # Jun–Nov
    "rabi":   {"start_month": 11, "end_month": 4},   # Nov–Apr
    "zaid":   {"start_month": 3, "end_month": 6},    # Mar–Jun
}

# Output schema keys that MUST be present
_REQUIRED_PLAN_KEYS = [
    "recommended_crop", "season", "confidence", "market_justification",
    "agronomic_justification", "weekly_plan", "risk_flags",
]


# ── Startup ───────────────────────────────────────────────────────────────────

def load_planner():
    """Load E5 + FAISS + Groq client. Called by app lifespan."""
    global _e5_model, _groq_client

    if _ST_AVAILABLE:
        logger.info("[planner] Loading multilingual-e5-large for RAG memory...")
        _e5_model = SentenceTransformer(settings.E5_MODEL_NAME)
        _build_guide_index()
        logger.info(f"[planner] Indexed {len(_guide_chunks)} guide chunks "
                    f"({'FAISS' if _faiss_index is not None else 'numpy'}).")
    else:
        logger.warning("[planner] E5 model unavailable — RAG search disabled.")

    try:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        logger.info("[planner] Groq client initialised.")
    except Exception as e:
        logger.error(f"[planner] Groq client init failed: {e}")


# ── RAG index builder ─────────────────────────────────────────────────────────

def _build_guide_index():
    global _guide_chunks, _guide_embeddings, _faiss_index
    data_dir = os.path.join(settings.DATA_DIR, "guides")

    chunks: List[Dict[str, Any]] = []
    for season in ["kharif", "rabi", "zaid"]:
        path = os.path.join(data_dir, f"{season}_cropguide.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"[planner] Could not read {season}_cropguide.json: {e}")
            continue

        for crop in data.get("crops", []):
            crop_name = crop.get("crop_name", "")
            soil_affinity = crop.get("preferred_soils", [])   # NEW field if present
            guide = crop.get("complete_farming_guide", {})

            for step_key, step_val in guide.items():
                if not isinstance(step_val, dict):
                    continue
                text_parts = [f"{crop_name} ({season}) — {step_val.get('title', step_key)}"]
                for k, v in step_val.items():
                    if isinstance(v, list):
                        text_parts.extend([str(i) for i in v])
                    elif isinstance(v, str):
                        text_parts.append(v)

                chunk_text = " ".join(text_parts)[:1200]
                chunks.append({
                    "text": chunk_text,
                    "season": season,
                    "crop": crop_name,
                    "step": step_key,
                    "water_req": crop.get("water_requirement_mm"),
                    "duration_days": crop.get("total_duration_days"),
                    "soil_affinity": soil_affinity,
                })

    if not chunks:
        logger.warning("[planner] No guide chunks found — RAG will return empty.")
        return

    texts = [f"passage: {c['text']}" for c in chunks]  # E5 passage prefix
    embeddings = _e5_model.encode(
        texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True
    )
    embeddings = embeddings.astype(np.float32)

    _guide_chunks = chunks
    _guide_embeddings = embeddings

    # Build FAISS inner-product index (L2-normalised = cosine similarity)
    if _FAISS_AVAILABLE:
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        _faiss_index = index


# ── RAG search ────────────────────────────────────────────────────────────────

def rag_search(
    query: str,
    season: str = "",
    crop_name: str = "",
    soil_type: str = "",
    top_k: int = 5,
) -> List[Dict]:
    """
    Semantic search over crop guides.
    Boosts: exact season (+0.07), exact crop (+0.12), soil affinity (+0.04).
    """
    if _e5_model is None or _guide_embeddings is None:
        return []

    query_emb = _e5_model.encode(
        [f"query: {query}"], normalize_embeddings=True
    ).astype(np.float32)

    if _faiss_index is not None:
        # FAISS search — returns distances and indices
        k = min(top_k * 4, len(_guide_chunks))
        scores_arr, indices = _faiss_index.search(query_emb, k)
        scores = scores_arr[0].tolist()
        candidate_indices = indices[0].tolist()
    else:
        # Numpy cosine fallback
        scores_list = np.dot(_guide_embeddings, query_emb.T).flatten().tolist()
        candidate_indices = list(range(len(scores_list)))
        scores = scores_list

    # Apply domain boosts
    boosted: Dict[int, float] = {}
    for i, idx in enumerate(candidate_indices):
        if idx < 0 or idx >= len(_guide_chunks):
            continue
        chunk = _guide_chunks[idx]
        s = scores[i]
        if season and chunk["season"].lower() == season.lower():
            s += 0.07
        if crop_name and chunk["crop"].lower() == crop_name.lower():
            s += 0.12
        if soil_type and soil_type.lower() in [x.lower() for x in chunk.get("soil_affinity", [])]:
            s += 0.15  # Increased boost for soil suitability
        boosted[idx] = s

    # Sort and return top_k
    sorted_indices = sorted(boosted, key=boosted.get, reverse=True)[:top_k]
    return [_guide_chunks[i] for i in sorted_indices]


# ── Main planner ────────────────────────────────────────────────────────────────

async def plan_crop(
    farm: Dict[str, Any],
    zone: Dict[str, Any],
    current_season: str,
    farmer_goal: str,
    weather_30d: Dict,
    query: str,
    lang: str = "en",
    recent_crops: Optional[List[str]] = None,   # crop rotation awareness
    budget_inr_per_acre: Optional[float] = None,
    mode: str = "new_season", # "new_season" or "existing_crop"
) -> Dict[str, Any]:
    """
    Full crop planning pipeline:
      1. Compute season window (days remaining)
      2. RAG search top guide chunks (season + soil-type boosted)
      3. Groq LLM (Llama 3.3) builds structured plan
      4. Validate & repair JSON output schema

    Returns JSON plan + multilingual plain summary
    """
    if _groq_client is None:
        return {"error": "Planner LLM not initialised (Groq client missing)", "status": "unavailable"}

    # ── Season window ─────────────────────────────────────────────────────────
    days_remaining = _days_remaining_in_season(current_season)

    # ── Typo correction & Preprocessing ─────────────────────────────────────
    typo_map = {"tice": "Rice", "suger": "Sugarcane", "sugercane": "Sugarcane", "paddy": "Rice"}
    processed_query = query
    for typo, correction in typo_map.items():
        processed_query = re.sub(rf"\b{typo}\b", correction, processed_query, flags=re.IGNORECASE)

    # ── RAG retrieval ─────────────────────────────────────────────────────────
    soil_type = zone.get("soil_type", "")
    guide_chunks = rag_search(
        query=processed_query,
        season=current_season,
        soil_type=soil_type,
        top_k=5,
    )
    context_text = "\n\n".join(
        [f"[{c['crop']} — {c['step']} | {c['season']}]\n{c['text']}" for c in guide_chunks]
    )

    # ── Rotation penalty list ─────────────────────────────────────────────
    rotation_note = ""
    if recent_crops:
        rotation_note = (
            f"\nCROP ROTATION CONSTRAINT: The farmer recently grew: {', '.join(recent_crops)}. "
            "Penalise recommending the same crop again in your confidence score and note this in risk_flags."
        )

    # ── Budget context ────────────────────────────────────────────────────
    budget_note = ""
    if budget_inr_per_acre:
        budget_note = f"\nFARMER BUDGET: ₹{budget_inr_per_acre:,.0f}/acre. Ensure recommended_crop fits within budget."

    # ── Build prompt ──────────────────────────────────────────────────────
    system_prompt = _build_system_prompt(lang, mode)
    user_message = f"""
FARM CONTEXT:
{json.dumps(farm, indent=2, default=str)}

ZONE CONTEXT:
{json.dumps(zone, indent=2, default=str)}

SEASON: {current_season}
DAYS REMAINING IN SEASON: {days_remaining}
FARMER GOAL: {farmer_goal}
WEATHER 30-DAY SUMMARY: {json.dumps(weather_30d, default=str)}
{rotation_note}
{budget_note}

RETRIEVED ICAR CROP KNOWLEDGE (TRUST THIS FOR WATER DATA):
{context_text}

AGRONOMIC GUARDRAILS:
- RICE (Paddy) is HIGH WATER INTENSITY (1200mm+). Never describe it as low water.
- SUGARCANE is HIGH WATER INTENSITY (1500mm+).
- MILLETS are LOW WATER INTENSITY.
- If the farm has limited water source, do NOT recommend Rice.

FARMER QUERY: {processed_query}

Respond with the JSON plan block first, then the plain summary in {lang}.
"""

    # ── Groq inference ─────────────────────────────────────────────
    groq_model = getattr(settings, "GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
    try:
        response = _groq_client.chat.completions.create(
            model=groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.2,
            max_tokens=2200,
        )
        raw = response.choices[0].message.content

        result = _extract_and_validate_json(raw)
        result["raw_response"] = raw
        result["rag_sources"] = [{"crop": c["crop"], "step": c["step"]} for c in guide_chunks]
        result["season_days_remaining"] = days_remaining
        return result

    except Exception as e:
        logger.error(f"[planner] Groq inference error: {e}")
        return {"error": str(e), "status": "failed"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_system_prompt(lang: str, mode: str = "new_season") -> str:
    if mode == "existing_crop":
        return f"""You are AquaSol's precision agronomy advisor for Indian farmers.
Your goal is to provide immediate, actionable advice for the crop CURRENTLY growing in the zone.
Use the retrieved ICAR knowledge to validate if the current growth stage matches the timeline.

MANDATORY OUTPUT FORMAT — return this JSON block FIRST (valid JSON):
{{
  "recommended_crop": "Current Crop Name",
  "season": "...",
  "confidence": 0.0,
  "market_justification": "Current market status for this crop",
  "agronomic_justification": "Advice based on current moisture and weather",
  "budget_fit": "Advice on cost-saving for this stage",
  "spacing_cm": "...",
  "plants_per_hectare": 0,
  "yield_estimate_kg_per_ha": 0,
  "estimated_revenue_inr_per_ha": 0,
  "weekly_plan": [{{"week": 1, "tasks": ["Specific task for this week"], "irrigation": "Specific irrigation advice", "fertilizer": "Specific fertilizer advice"}}],
  "fertilizer_schedule": ["Immediate fertilizer needs"],
  "irrigation_plan": ["Immediate irrigation strategy"],
  "risk_flags": ["Pest or weather risks for this week"],
  "alternative_crop": "N/A"
}}

After the JSON, write a plain farmer-friendly summary in: {lang} focusing on WHAT TO DO THIS WEEK.
Rules:
- Max 100 words, simple language, no technical jargon
- Do NOT mention AI, ML, models, or predictions
- Language: {lang}
"""

    return f"""You are AquaSol's precision crop planning intelligence for Indian farmers.
You have access to ICAR-validated crop knowledge retrieved for you.
Your goal is to recommend a NEW crop for the upcoming cycle that MAXIMIZES both YIELD and PROFIT based on the soil type and season.

ECONOMIC INTELLIGENCE:
- Evaluate the "Profitability Index" for each candidate crop.
- Consider market demand, duration (faster turn-around = more cycles), and input costs (water/fertilizer).
- If the soil is highly suitable for a high-value crop (like Cotton or Sugarcane), prioritize it.

MANDATORY OUTPUT FORMAT — return this JSON block FIRST:
{{
  "recommended_crop": "...",
  "season": "...",
  "confidence": 0.0,
  "market_justification": "Why this crop is profitable right now",
  "agronomic_justification": "Why this soil is perfect for this crop",
  "budget_fit": "Analysis of ROI vs Input Costs",
  "spacing_cm": "row x plant",
  "plants_per_hectare": 0,
  "yield_estimate_kg_per_ha": 0,
  "estimated_revenue_inr_per_ha": 0,
  "weekly_plan": [{{"week": 1, "tasks": [], "irrigation": "...", "fertilizer": "..."}}],
  "fertilizer_schedule": [],
  "irrigation_plan": [],
  "risk_flags": [],
  "alternative_crop": "..."
}}

After the JSON, write a plain farmer-friendly summary in: {lang}
Rules:
- Max 100 words, simple language, no technical jargon
- Do NOT mention AI, ML, models, or predictions
- Language: {lang}
"""


def _extract_and_validate_json(raw: str) -> Dict:
    """Extract JSON block and validate required keys. Repair if possible."""
    # Try code-fenced JSON first
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        # Find the largest {...} block
        candidate_match = re.search(r"\{.*\}", raw, re.DOTALL)
        candidate = candidate_match.group() if candidate_match else ""

    if candidate:
        # Strip trailing commas before } or ] to fix common LLM JSON errors
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            data = json.loads(candidate)
            # Validate required keys
            missing = [k for k in _REQUIRED_PLAN_KEYS if k not in data]
            if missing:
                data["_schema_warnings"] = f"Missing keys: {missing}"
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"[planner] JSON parse failed ({e}) — returning raw text.")

    return {"raw": raw, "status": "parse_error"}


def _days_remaining_in_season(season: str) -> int:
    """Approximate days remaining in the current agricultural season."""
    now = datetime.utcnow()
    window = _SEASON_WINDOWS.get(season.lower())
    if not window:
        return 90  # default

    end_month = window["end_month"]
    end_year = now.year if end_month >= now.month else now.year + 1

    try:
        end_date = datetime(end_year, end_month, 28)  # conservative end date
        days_left = (end_date - now).days
        return max(0, days_left)
    except Exception:
        return 90

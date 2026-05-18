"""
Service — Chatbot (Solu) v2
Brain: HuggingFace Inference API (Mistral/LLaMA)
Memory: FAISS RAG (ICAR Crop Guides)
Ears: Groq Whisper (voice → text)
Voice: edge-tts / gTTS (text → speech)
i18n: en / kn / hi / te / mr
"""
import os
import uuid
import json
import tempfile
import asyncio
from typing import Optional, Dict, Any, List
from huggingface_hub import InferenceClient
from groq import Groq
# import whisper (Moved to lazy import to avoid torch dependency issues on some Windows setups)
from backend.config.settings import get_settings
from backend.utils.logger import logger
from backend.plugins.ai.planner.crop_planner import rag_search

settings = get_settings()

# ── Ears: Groq Whisper ────────────────────────────────────────────────────────
_groq_client = Groq(api_key=settings.GROQ_API_KEY)
_local_whisper = None

def _get_local_whisper():
    global _local_whisper
    if _local_whisper is None:
        try:
            import whisper
            _local_whisper = whisper.load_model("base")
        except Exception as e:
            logger.error(f"[chatbot] Failed to load local whisper model: {e}")
            return None
    return _local_whisper


# ── Brain: Groq (Llama 3.3) ───────────────────────────────────────────────────
def _get_groq_brain_completion(messages: List[Dict[str, str]], voice_out: bool = False):
    """
    Standard Groq Reasoning call. 
    Uses llama-3.3-70b-versatile for high reasoning capability.
    """
    model = getattr(settings, "GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
    try:
        response = _groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=500 if not voice_out else 150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[chatbot] Groq Brain error: {e}")
        return None

LANG_NAMES = {
    "en": "English", "kn": "Kannada",
    "hi": "Hindi",   "te": "Telugu",
    "ta": "Tamil",   "mr": "Marathi"
}


SOLU_SYSTEM_PROMPT = """You are Solu, AquaSol's expert agricultural digital twin.

PERSONALITY:
- Warm, patient, and highly knowledgeable.
- Speak like a trusted local expert with a PhD in Agronomy.
- Use simple analogies but provide precise data when possible.
- Match language exactly: {lang_name}.

PLAN AWARENESS:
- Always check the "active_plan_task" in the context.
- If a plan task exists for the current zone, prioritize explaining it as the primary recommendation.
- The Intelligence Engine has already validated this plan against real-time sensor data.

AGRONOMIC GUARDRAILS (STRICT):
- RICE (Paddy) is HIGH WATER INTENSITY. It requires constant moisture (1200mm+).
- SUGARCANE is HIGH WATER INTENSITY (1500mm+).
- MILLETS and PULSES are LOW WATER INTENSITY.
- Never recommend Rice or Sugarcane if the user mentions water scarcity or limited supply.
- If you recommend a crop, ensure it aligns with the current season ({lang_name} context).

AGENTIC RAG CAPABILITIES:
1. You have real-time access to the farm system state (sensors, stages, anomalies).
2. You have "Expert Memory" — context provided from ICAR agricultural guides.
3. Use the Expert Memory to ground your answers in technical reality.

RULES:
- If the user greets you (e.g., "hi", "hello"), respond warmly and ask how you can help with their farm today.
- If the user asks questions UNRELATED to farming, agriculture, crops, soil, or the AquaSol system, politely decline and redirect them to ask about their farm or crops.
- End every response with ONE actionable suggestion based on the active plan or sensor data.
- If an anomaly is detected, prioritize explaining the risk.
- Do NOT mention AI, tokens, or retrieved chunks.
- Tone: Empathetic but practical.
"""

LANG_VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-MadhurNeural",
    "kn": "kn-IN-SapnaNeural",
    "te": "te-IN-ShrutiNeural",
    "ta": "ta-IN-PallaviNeural",
    "mr": "mr-IN-AarohiNeural",
}


async def transcribe_audio(audio_bytes: bytes, filename: str = "voice.webm") -> str:
    """
    STT using Groq Whisper (Cloud) with local fallback.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[-1], delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Try Groq Cloud Whisper first (fastest)
        try:
            with open(tmp_path, "rb") as file:
                transcription = _groq_client.audio.transcriptions.create(
                    file=(filename, file.read()),
                    model=settings.GROQ_WHISPER_MODEL,
                )
            os.unlink(tmp_path)
            return transcription.text.strip()
        except Exception as e:
            logger.warning(f"[chatbot] Groq Whisper failed, falling back to local: {e}")
            
        # Local Fallback
        def _transcribe():
            model = _get_local_whisper()
            result = model.transcribe(tmp_path)
            return result["text"]

        transcription = await asyncio.to_thread(_transcribe)
        os.unlink(tmp_path)
        return transcription.strip()
    except Exception as e:
        logger.error(f"[whisper] Transcription fatal error: {e}")
        return ""


async def chat(
    message: str,
    context: Dict[str, Any],
    lang: str = "en",
    voice_out: bool = False,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Solu v3: Groq Brain (Llama 3.3) + Agentic RAG Memory + DB i18n.
    Returns: { reply, lang, audio_path, rag_used }
    """
    from backend.services.i18n_service import get_localized_message

    # ── 1. RAG Search (Agentic Retrieval) ─────────────────────────────────────
    # We perform a semantic search to ground the "Expert" reasoning.
    knowledge_chunks = rag_search(query=message, top_k=3)
    knowledge_text = "\n\n".join([f"[{c['crop']}]: {c['text']}" for c in knowledge_chunks])
    if not knowledge_text:
        knowledge_text = "No specific guide found. Use general best practices."

    # ── 2. Build Prompt ───────────────────────────────────────────────────────
    lang_name = LANG_NAMES.get(lang, "English")
    system = SOLU_SYSTEM_PROMPT.format(lang_name=lang_name)
    
    # Enhanced context with RAG memory
    prompt_context = f"""
    FARM STATE:
    {json.dumps(context, indent=2, default=str)}

    EXPERT MEMORY:
    {knowledge_text}
    """

    messages = [
        {"role": "system", "content": system},
    ]
    
    if conversation_history:
        messages.extend(conversation_history[-6:])
    
    messages.append({"role": "user", "content": f"CONTEXT:\n{prompt_context}\n\nUSER MESSAGE: {message}"})

    # ── 3. Groq Reasoning ────────────────────────────────────────────────────
    reply = _get_groq_brain_completion(messages, voice_out)
    
    if not reply:
        # Fallback to DB-localized error message
        reply = await get_localized_message("chatbot_error_generic", lang)

    # ── 4. TTS ───────────────────────────────────────────────────────────────
    audio_path = None
    if voice_out:
        audio_path = await _generate_tts(reply, lang)

    return {
        "reply": reply, 
        "lang": lang, 
        "audio_path": audio_path,
        "rag_used": len(knowledge_chunks) > 0
    }


async def _generate_tts(text: str, lang: str) -> Optional[str]:
    """
    Multilingual TTS using gTTS.
    """
    try:
        from gtts import gTTS
        audio_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "audio")
        os.makedirs(audio_dir, exist_ok=True)

        filename = f"solu_{uuid.uuid4().hex[:8]}.mp3"
        out_path = os.path.join(audio_dir, filename)

        def _create_tts():
            # gTTS expects 'en', 'hi', 'kn', 'te'
            tts = gTTS(text=text, lang=lang)
            tts.save(out_path)

        await asyncio.to_thread(_create_tts)
        return f"/static/audio/{filename}"
    except Exception as e:
        logger.warning(f"[tts] gTTS error: {e}")
        return None

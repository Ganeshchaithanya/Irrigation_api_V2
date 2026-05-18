"""
API Router — Chatbot (Solu)
POST /chat              → text chat (Groq LLaMA 3.3)
POST /chat/voice        → voice input (Groq Whisper) → reply + TTS
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from backend.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.models.user import User
from backend.models.farm import Farm, Zone
from backend.services.chatbot import chat, transcribe_audio
from backend.services.context_builder import build_chat_context
from backend.services.weather import get_weather
from backend.schemas.dashboard import ChatRequest, ChatResponse
from backend.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["Chatbot — Solu"])


async def _get_user_context(current_user: User, db: AsyncSession) -> dict:
    """Fetch farm + zone IDs + weather for context injection."""
    farm_result = await db.execute(
        select(Farm).where(Farm.user_id == current_user.id)
    )
    farm = farm_result.scalars().first()
    if not farm:
        return {"farm_name": "Unknown", "zones": [], "weather": {}, "active_alerts": [], "last_decision": None, "timestamp": ""}

    zones_result = await db.execute(
        select(Zone.id).where(Zone.farm_id == farm.id, Zone.status == "active")
    )
    zone_ids = [str(row) for row in zones_result.scalars().all()]

    weather = {}
    if farm.latitude and farm.longitude:
        weather = await get_weather(farm.latitude, farm.longitude, lang=current_user.preferred_lang)

    return await build_chat_context(str(farm.id), farm.name, zone_ids, weather)


@router.post("", response_model=ChatResponse)
async def text_chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Text-based chat with Solu.
    lang: en | kn | hi | te | mr
    """
    lang = payload.lang or current_user.preferred_lang
    context = await _get_user_context(current_user, db)

    result = await chat(
        message=payload.message,
        context=context,
        lang=lang,
        voice_out=payload.voice_mode,
    )

    return ChatResponse(
        reply=result["reply"],
        lang=result["lang"],
        audio_url=result.get("audio_path"),
    )


@router.post("/voice", response_model=ChatResponse)
async def voice_chat(
    audio: UploadFile = File(...),
    lang: str = Form(default="en"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Voice-based chat:
    1. Groq Whisper transcribes audio → text
    2. Groq LLaMA replies
    3. edge-tts generates voice response
    """
    if audio.content_type not in (
        "audio/webm", "audio/mp3", "audio/mpeg",
        "audio/wav", "audio/ogg", "audio/m4a", "audio/mp4"
    ):
        raise HTTPException(400, f"Unsupported audio type: {audio.content_type}")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(400, "Empty audio file.")

    # Whisper STT
    transcribed_text = await transcribe_audio(audio_bytes, audio.filename or "voice.webm")
    if not transcribed_text:
        raise HTTPException(422, "Could not transcribe audio. Please speak clearly.")

    logger.info(f"[whisper] User({current_user.id}) said: {transcribed_text[:80]}")

    lang = lang or current_user.preferred_lang
    context = await _get_user_context(current_user, db)

    # Chat + TTS
    result = await chat(
        message=transcribed_text,
        context=context,
        lang=lang,
        voice_out=True,
    )

    return ChatResponse(
        reply=result["reply"],
        lang=result["lang"],
        audio_url=result.get("audio_path"),
    )

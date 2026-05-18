"""
Service — Diary AI (Solu)
Uses Groq to provide localized insights/advice for farm diary entries.
"""
import json
from typing import Optional
from groq import Groq
from backend.config.settings import get_settings
from backend.utils.logger import logger

settings = get_settings()

_groq_client = None

def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    try:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        return _groq_client
    except Exception as e:
        logger.error(f"[diary_ai] Groq client init failed: {e}")
        return None

LANG_NAMES = {
    "en": "English", "kn": "Kannada",
    "hi": "Hindi",   "te": "Telugu",
    "ta": "Tamil",   "mr": "Marathi"
}

_SYSTEM_PROMPT = """You are Solu, AquaSol's agricultural AI.
The farmer has just added a diary entry. Provide a brief, supportive, and technical insight or piece of advice based on this entry.

Rules:
- Max 30 words.
- Tone: Helpful and expert.
- Language MUST be: {lang_name}.
- Do not mention AI or models.
"""

async def generate_diary_insight(
    title: str,
    content: Optional[str],
    category: str,
    lang: str = "en"
) -> str:
    """
    Generates a localized AI insight for a diary entry using Groq.
    """
    lang_name = LANG_NAMES.get(lang, "English")
    
    user_message = f"Category: {category}\nTitle: {title}\nContent: {content or 'No details provided.'}"
    
    client = _get_groq_client()
    if client:
        try:
            model = getattr(settings, "GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT.format(lang_name=lang_name)},
                    {"role": "user",   "content": user_message},
                ],
                temperature=0.3,
                max_tokens=150,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"[diary_ai] Groq Error: {e}")
    
    return "" # No insight if AI fails

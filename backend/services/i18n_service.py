"""
Service — i18n Translation Hardener
Fetches localized strings from the message_templates database table.
Supports English, Hindi, Kannada, and Telugu.
"""
from typing import Dict, Optional
from sqlalchemy import select
from backend.db.session import AsyncSessionLocal
from backend.models.i18n import MessageTemplate
from backend.utils.logger import logger

# Simple in-memory cache for templates (Code -> {en, hi, kn, te})
_template_cache: Dict[str, Dict[str, str]] = {}

async def get_localized_message(code: str, lang: str = "en") -> str:
    """
    Fetches the translation for a given code and language.
    Falls back to English if the language-specific translation is missing.
    Returns the code itself if no template exists.
    """
    # 1. Check cache first
    if code in _template_cache:
        return _template_cache[code].get(lang) or _template_cache[code].get("en", code)

    # 2. Fetch from DB
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(MessageTemplate).where(MessageTemplate.code == code)
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            
            if template:
                data = {
                    "en": template.en,
                    "hi": template.hi,
                    "kn": template.kn,
                    "te": template.te,
                    "ta": template.ta,
                    "mr": template.mr
                }
                _template_cache[code] = data
                return data.get(lang) or data.get("en", code)
            
            # If not found in DB, return code as fallback
            return code
    except Exception as e:
        logger.error(f"[i18n] Error fetching template '{code}': {e}")
        return code

async def refresh_i18n_cache():
    """Wipes the local cache — useful if templates are updated in DB."""
    global _template_cache
    _template_cache = {}
    logger.info("[i18n] Translation cache cleared.")

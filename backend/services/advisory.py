"""
Service — Advisory Simplifier (v3)
Converts structured AI outputs → single plain-language farmer instruction.
Brain: Groq (Llama 3.3)
i18n: en / kn / hi / te
"""
import json
from typing import Dict, Any, Optional
from groq import Groq
from backend.config.settings import get_settings
from backend.utils.logger import logger

settings = get_settings()

# ── Groq client (lazy init) ──────────────────────────────────────────────────
_groq_client = None

def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    try:
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        return _groq_client
    except Exception as e:
        logger.error(f"[advisory] Groq client init failed: {e}")
        return None


LANG_NAMES = {
    "en": "English", "kn": "Kannada",
    "hi": "Hindi",   "te": "Telugu",
    "ta": "Tamil",   "mr": "Marathi"
}

_SYSTEM_PROMPT = """You are an advisory simplifier for a precision farm irrigation system.
Convert the structured data into ONE clear instruction for the farmer.

Rules:
- Imperative mood, plain language, NO technical jargon
- Max 20 words
- Never mention confidence scores, model names, sensor IDs, or AI
- Language MUST be: {lang_name}

Examples (English):
- "Open Zone A valve for 25 minutes — soil is getting dry."
- "No irrigation needed for Zone B — rain expected soon."
- "Check Zone C sensor — readings seem abnormal."
"""


async def simplify_advisory(
    decision: str,
    duration_min: int,
    stage: str,
    moisture_now: float,
    moisture_target: float,
    rain_prob_6h: float,
    confidence: float,
    zone_name: str = "Zone A",
    lang: str = "en",
    anomaly_type: Optional[str] = None,
) -> str:
    """
    Returns a single advisory sentence in the specified language (Groq Brain).
    """
    lang_name = LANG_NAMES.get(lang, "English")

    input_data = {
        "decision": decision,
        "duration_min": duration_min,
        "crop_stage": stage,
        "moisture_now_pct": round(moisture_now, 1),
        "moisture_target_pct": round(moisture_target, 1),
        "rain_prob_6h": round(rain_prob_6h, 2),
        "zone_name": zone_name,
        "anomaly_detected": anomaly_type,
    }

    client = _get_groq_client()
    if client is not None:
        model = getattr(settings, "GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT.format(lang_name=lang_name)},
                    {"role": "user",   "content": json.dumps(input_data)},
                ],
                temperature=0.1,
                max_tokens=100,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"[advisory] Groq Error: {e} — using template fallback.")

    # ── Template fallback (always works) ──────────────────────────────────────
    return _template_advisory(decision, duration_min, zone_name, anomaly_type, lang)


def _template_advisory(
    decision: str,
    duration_min: int,
    zone_name: str,
    anomaly_type: Optional[str],
    lang: str = "en",
) -> str:
    """Rule-based advisory sentence — multi-lingual fallback."""
    templates = {
        "en": {
            "anomaly": "Check {zone} sensor — readings seem abnormal ({info}).",
            "irrigate": "Open {zone} valve for {min} minutes — soil needs water.",
            "delay": "Monitor {zone} — irrigation may be needed soon.",
            "skip": "No irrigation needed for {zone} right now."
        },
        "hi": {
            "anomaly": "{zone} सेंसर की जांच करें — रीडिंग असामान्य लग रही है ({info})।",
            "irrigate": "{zone} वाल्व को {min} मिनट के लिए खोलें — मिट्टी को पानी की जरूरत है।",
            "delay": "{zone} की निगरानी करें — जल्द ही सिंचाई की आवश्यकता हो सकती है।",
            "skip": "{zone} के लिए अभी सिंचाई की आवश्यकता नहीं है।"
        },
        "kn": {
            "anomaly": "{zone} ಸೆನ್ಸರ್ ಪರಿಶೀಲಿಸಿ — ರೀಡಿಂಗ್ ಅಸಹಜವಾಗಿದೆ ({info}).",
            "irrigate": "{zone} ವಾಲ್ವ್ ಅನ್ನು {min} ನಿಮಿಷಗಳ ಕಾಲ ತೆರೆಯಿರಿ — ಮಣ್ಣಿಗೆ ನೀರಿನ ಅವಶ್ಯಕತೆಯಿದೆ.",
            "delay": "{zone} ಗಮನಿಸಿ — ಶೀಘ್ರದಲ್ಲೇ ನೀರಾವರಿ ಬೇಕಾಗಬಹುದು.",
            "skip": "{zone} ಗೆ ಈಗ ನೀರಾವರಿ ಅಗತ್ಯವಿಲ್ಲ."
        },
        "te": {
            "anomaly": "{zone} ಸೆನ್ಸార్‌ను తనిఖీ చేయండి — రీడింగ్ అసాధారణంగా ఉంది ({info}).",
            "irrigate": "{zone} వాల్వ్‌ను {min} నిమిషాల పాటు తెరవండి — నేలకు నీరు అవసరం.",
            "delay": "{zone}ను పర్యవేక్షించండి — త్వరలో నీటి పారుదల అవసరం కావచ్చు.",
            "skip": "{zone} కోసం ఇప్పుడు నీటి పారుదల అవసరం లేదు."
        },
        "ta": {
            "anomaly": "{zone} சென்சாரைச் சரிபார்க்கவும் — அளவீடுகள் அசாதாரணமாகத் தெரிகிறது ({info}).",
            "irrigate": "{zone} வால்வை {min} நிமிடங்கள் திறக்கவும் — மண்ணிற்குத் தண்ணீர் தேவை.",
            "delay": "{zone} ஐக் கண்காணிக்கவும் — விரைவில் பாசனம் தேவைப்படலாம்.",
            "skip": "{zone} க்கு இப்போது பாசனம் தேவையில்லை."
        },
        "mr": {
            "anomaly": "{zone} सेन्सर तपासा — रीडिंग असामान्य वाटत आहे ({info})।",
            "irrigate": "{zone} व्हॉल्व्ह {min} मिनिटांसाठी उघडा — मातीला पाण्याची गरज आहे।",
            "delay": "{zone} वर लक्ष ठेवा — लवकरच सिंचनाची गरज भासू शकते।",
            "skip": "{zone} साठी आता सिंचनाची गरज नाही।"
        }
    }

    t = templates.get(lang, templates["en"])
    
    if anomaly_type and anomaly_type not in ("sensor_stuck", "slow_drift"):
        info = anomaly_type.replace('_', ' ')
        return t["anomaly"].format(zone=zone_name, info=info)
    
    if decision == "irrigate":
        return t["irrigate"].format(zone=zone_name, min=duration_min)
    if decision == "delay":
        return t["delay"].format(zone=zone_name)
    
    return t["skip"].format(zone=zone_name)

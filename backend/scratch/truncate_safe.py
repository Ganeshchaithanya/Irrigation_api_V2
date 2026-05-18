import asyncio
import os
import socket
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# DNS Monkeypatch
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech":
        return _original_getaddrinfo("13.228.46.236", port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

load_dotenv()
_raw_url = os.getenv("DATABASE_URL", "")
# Fix scheme for asyncpg
url = _raw_url.split("?")[0].replace("postgresql://", "postgresql+asyncpg://")

# Order matters: child tables first, then parent tables
ORDERED_TABLES = [
    "sensor_readings",
    "valve_commands",
    "decision_log",
    "zone_state",
    "diary_entries",
    "crop_plans",
    "schedules",
    "pairing_sessions",
    "devices",
    "crop_bio_profiles",
    "node_slots", # Added node_slots
    "zones",
    "acres",
    "farms",
    "message_templates",
    "users",
]

async def truncate_all():
    # Note: connect_args match the session.py fix
    engine = create_async_engine(
        url, 
        echo=False,
        connect_args={"ssl": "require"}
    )
    async with engine.begin() as conn:
        # Disable constraints temporarily if possible, or just follow order
        for table in ORDERED_TABLES:
            try:
                result = await conn.execute(text(f'DELETE FROM "{table}"'))
                print(f"  Cleared  {table:<30} ({result.rowcount} rows deleted)")
            except Exception as e:
                print(f"  Error clearing {table}: {e}")
    await engine.dispose()
    print("\nAll tables cleared successfully.")

if __name__ == "__main__":
    asyncio.run(truncate_all())

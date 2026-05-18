"""
Async SQLAlchemy engine + session factory for Neon PostgreSQL.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator
from backend.config.settings import get_settings

settings = get_settings()

# Convert postgresql:// → postgresql+asyncpg://
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
# Remove params — asyncpg handles SSL natively via connect_args
if any(p in _db_url for p in ["channel_binding", "sslmode"]):
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(_db_url)
    params = parse_qs(parsed.query)
    params.pop("channel_binding", None)
    params.pop("sslmode", None)
    new_query = urlencode({k: v[0] for k, v in params.items()})
    _db_url = urlunparse(parsed._replace(query=new_query))
import socket

# DNS Monkeypatch to bypass broken system DNS for Neon DB
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech":
        return _original_getaddrinfo("13.228.46.236", port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"ssl": "require"},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

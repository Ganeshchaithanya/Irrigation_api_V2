import asyncio, os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
load_dotenv()
url = os.getenv("DATABASE_URL", "").split("?")[0].replace("postgresql://", "postgresql+asyncpg://")

async def check():
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'"))
        tables = [row[0] for row in r.all()]
        print(f"{'Table':<30} {'Rows':>6}")
        print("-" * 38)
        for t in tables:
            cnt = await conn.execute(text(f'SELECT COUNT(*) FROM "{t}"'))
            print(f"{t:<30} {cnt.scalar():>6}")
    await engine.dispose()

asyncio.run(check())

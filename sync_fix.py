from sqlalchemy import create_engine, text
from backend.config.settings import get_settings

e = create_engine(get_settings().DATABASE_URL.replace('+asyncpg', ''))
with e.begin() as c:
    c.execute(text("DELETE FROM crop_plans WHERE farm_id IS NULL"))

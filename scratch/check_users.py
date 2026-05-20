import os
from sqlalchemy import create_engine, text

db_url = "postgresql://neondb_owner:npg_Lbf9rKJHMSW3@ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(db_url)

with engine.connect() as conn:
    print("--- USERS ---")
    users = conn.execute(text("SELECT id, email, name, is_active FROM users")).fetchall()
    for u in users:
        print(u)
    
    print("\n--- FARMS ---")
    farms = conn.execute(text("SELECT id, user_id, name, location FROM farms")).fetchall()
    for f in farms:
        print(f)

import os
from sqlalchemy import create_engine, text

db_url = "postgresql://neondb_owner:npg_Lbf9rKJHMSW3@ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(db_url)

with engine.connect() as conn:
    print("--- USERS ---")
    for row in conn.execute(text("SELECT id, email, name, phone FROM users")):
        print(row)
        
    print("\n--- FARMS ---")
    for row in conn.execute(text("SELECT id, name, user_id FROM farms")):
        print(row)
        
    print("\n--- ZONES ---")
    for row in conn.execute(text("SELECT id, name, farm_id FROM zones")):
        print(row)
        
    print("\n--- NODE SLOTS ---")
    for row in conn.execute(text("SELECT id, name, zone_id FROM node_slots")):
        print(row)

    print("\n--- DEVICES ---")
    for row in conn.execute(text("SELECT id, device_uid, mac_address, status, is_claimed, farm_id, node_slot_id, role, pairing_code FROM devices")):
        print(row)
        
    print("\n--- PAIRING SESSIONS ---")
    for row in conn.execute(text("SELECT id, pairing_code, farm_id, zone_id, node_slot_id, is_used, expires_at FROM pairing_sessions")):
        print(row)

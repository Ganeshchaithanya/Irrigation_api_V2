import asyncio
import sys
import os
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.db.session import engine

async def migrate():
    print("Running migrations...")
    async with engine.begin() as conn:
        # Add missing columns to 'farms' table
        try:
            await conn.execute(text("ALTER TABLE farms ADD COLUMN IF NOT EXISTS total_acres INTEGER DEFAULT 1;"))
            await conn.execute(text("ALTER TABLE farms ADD COLUMN IF NOT EXISTS water_source VARCHAR;"))
            print("Updated 'farms' table.")
        except Exception as e:
            print(f"Error updating 'farms': {e}")

        # Add missing columns to 'users' table
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(5);"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_lang VARCHAR DEFAULT 'en';"))
            print("Updated 'users' table.")
        except Exception as e:
            print(f"Error updating 'users': {e}")

        # Add missing columns to 'zones' table (node mapping)
        try:
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS season VARCHAR;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS mode VARCHAR(10) DEFAULT 'auto';"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS operating_mode VARCHAR(50) DEFAULT 'active';"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS area_acres NUMERIC(6, 2);"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS sowing_date DATE;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS current_stage VARCHAR DEFAULT 'early';"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS expected_harvest DATE;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS morning_window VARCHAR;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS evening_window VARCHAR;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS min_moisture_threshold NUMERIC(5, 2) DEFAULT 15.0;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS max_moisture_threshold NUMERIC(5, 2) DEFAULT 85.0;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS max_irrigation_duration_sec INTEGER DEFAULT 3600;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS sensor_depth_cm INTEGER DEFAULT 10;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS root_depth_cm INTEGER DEFAULT 30;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS application_rate_mm_hr NUMERIC(5, 2) DEFAULT 2.0;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS efficiency NUMERIC(3, 2) DEFAULT 0.90;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active';"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS start_node VARCHAR;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS mid_node VARCHAR;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS end_node VARCHAR;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS acre_id UUID REFERENCES acres(id) ON DELETE SET NULL;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS soil_type VARCHAR;"))
            await conn.execute(text("ALTER TABLE zones ADD COLUMN IF NOT EXISTS irrigation_type VARCHAR DEFAULT 'drip';"))
            print("Updated 'zones' table.")
        except Exception as e:
            print(f"Error updating 'zones': {e}")

        # Add missing columns to 'devices' table
        try:
            await conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_uid VARCHAR;"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS pairing_code VARCHAR;"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS node_label VARCHAR;"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active';"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_master BOOLEAN DEFAULT FALSE;"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS trust_score NUMERIC(4, 3) DEFAULT 1.0;"))
            print("Updated 'devices' table.")
        except Exception as e:
            print(f"Error updating 'devices': {e}")

        # Add missing columns to 'diary_entries' table
        try:
            await conn.execute(text("ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS is_subsidy_relevant BOOLEAN DEFAULT FALSE;"))
            await conn.execute(text("ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS subsidy_status VARCHAR;"))
            await conn.execute(text("ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS cost NUMERIC(10, 2) DEFAULT 0.0;"))
            await conn.execute(text("ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS payment_status VARCHAR DEFAULT 'unpaid';"))
            await conn.execute(text("ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS payment_reference VARCHAR;"))
            await conn.execute(text("ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS record_data VARCHAR;"))
            print("Updated 'diary_entries' table.")
        except Exception as e:
            print(f"Error updating 'diary_entries': {e}")

        # Create 'sensor_readings' table if it doesn't exist
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    time TIMESTAMP WITH TIME ZONE NOT NULL,
                    device_id UUID NOT NULL REFERENCES devices(id),
                    zone_id UUID NOT NULL REFERENCES zones(id),
                    farm_id UUID NOT NULL REFERENCES farms(id),
                    soil_moisture NUMERIC(5, 2),
                    temperature NUMERIC(5, 2),
                    humidity NUMERIC(5, 2),
                    valve_status BOOLEAN DEFAULT FALSE,
                    flow_rate NUMERIC(8, 3),
                    total_water NUMERIC(10, 3),
                    rain_detected BOOLEAN,
                    battery_pct NUMERIC(5, 2),
                    solar_pct NUMERIC(5, 2),
                    solar_voltage NUMERIC(5, 2),
                    is_virtual BOOLEAN DEFAULT FALSE,
                    raw_payload JSONB,
                    PRIMARY KEY (time, device_id)
                );
            """))
            print("Created 'sensor_readings' table.")
        except Exception as e:
            print(f"Error creating 'sensor_readings': {e}")

        # Create 'schedules' table if it doesn't exist
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id UUID PRIMARY KEY,
                    farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
                    zone_id UUID REFERENCES zones(id) ON DELETE CASCADE,
                    acre_id UUID REFERENCES acres(id) ON DELETE CASCADE,
                    label VARCHAR,
                    time VARCHAR NOT NULL,
                    days JSONB NOT NULL,
                    duration_min INTEGER DEFAULT 30,
                    intensity INTEGER DEFAULT 80,
                    mode VARCHAR DEFAULT 'manual',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("Created 'schedules' table.")
        except Exception as e:
            print(f"Error creating 'schedules': {e}")

    print("Migration complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())

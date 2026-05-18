
import asyncio
from sqlalchemy import text
from backend.db.session import AsyncSessionLocal

async def update_db():
    async with AsyncSessionLocal() as db:
        print("Checking valve_commands table...")
        
        # 1. Add node_slot_id to valve_commands
        try:
            await db.execute(text("ALTER TABLE valve_commands ADD COLUMN node_slot_id UUID REFERENCES node_slots(id);"))
            await db.commit()
            print("Successfully added node_slot_id to valve_commands.")
        except Exception as e:
            await db.rollback()
            if "already exists" in str(e):
                print("node_slot_id already exists in valve_commands.")
            else:
                print(f"Error adding column to valve_commands: {e}")

        # 2. Check if sensor_readings has node_slot_id (it should, but just in case)
        try:
            # PostgreSQL syntax to check column existence and add if missing
            await db.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='sensor_readings' AND column_name='node_slot_id') THEN
                        ALTER TABLE sensor_readings ADD COLUMN node_slot_id UUID REFERENCES node_slots(id);
                    END IF;
                END $$;
            """))
            await db.commit()
            print("Checked sensor_readings for node_slot_id.")
        except Exception as e:
            await db.rollback()
            print(f"Error checking sensor_readings: {e}")

if __name__ == "__main__":
    asyncio.run(update_db())

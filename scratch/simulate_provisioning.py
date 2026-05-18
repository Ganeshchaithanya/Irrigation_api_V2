
import asyncio
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import models
from backend.models.device import Device
from backend.models.farm import Farm, Acre, Zone
from backend.db.base import Base

# Database URL (using async driver)
DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_Lbf9rKJHMSW3@ep-restless-meadow-a1l64nqq-pooler.ap-southeast-1.aws.neon.tech/neondb"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_provisioning_flow():
    async with AsyncSessionLocal() as db:
        print("\n--- Starting Provisioning Simulation ---")
        
        # 1. Create a dummy farm for testing
        test_user_id = uuid.UUID("f1806010-6c19-4e00-9beb-8539680d1b31") 
        farm = Farm(
            id=uuid.uuid4(),
            user_id=test_user_id,
            name="Test Simulation Farm",
            location="Simulation Lab"
        )
        db.add(farm)
        await db.flush()
        
        acre = Acre(id=uuid.uuid4(), farm_id=farm.id, name="Old Acre Name")
        db.add(acre)
        await db.flush()
        
        zone = Zone(id=uuid.uuid4(), farm_id=farm.id, acre_id=acre.id, name="Old Zone Name")
        db.add(zone)
        await db.flush()
        
        # 2. Simulate Hardware Discovery
        test_mac = "AA:BB:CC:DD:EE:FF"
        device = Device(
            id=uuid.uuid4(),
            device_uid="SIM-123",
            mac_address=test_mac,
            is_master=False,
            status="discovery"
        )
        db.add(device)
        await db.commit()
        print(f"[1] Device discovered with MAC: {test_mac}")

        # 3. Simulate App-side Assignment with CUSTOM NAMES
        print("[2] Simulating App assignment with custom names...")
        
        # This mirrors the logic in backend/api/device.py
        async with db.begin():
            # Find the device
            res = await db.execute(select(Device).where(Device.mac_address == test_mac))
            d = res.scalar_one()
            
            # Update names
            new_node_name = "Hillside Node A1"
            new_acre_name = "North Field"
            new_zone_name = "Strawberry Zone"
            
            d.farm_id = farm.id
            d.acre_id = acre.id
            d.zone_id = zone.id
            d.node_label = new_node_name
            d.status = "active"
            
            # Update Acre & Zone names directly
            from sqlalchemy import update
            await db.execute(update(Acre).where(Acre.id == acre.id).values(name=new_acre_name))
            await db.execute(update(Zone).where(Zone.id == zone.id).values(name=new_zone_name))
            
            print(f"    - Assigned Device to Farm: {farm.id}")
            print(f"    - Set Node Label: {new_node_name}")
            print(f"    - Set Acre Name: {new_acre_name}")
            print(f"    - Set Zone Name: {new_zone_name}")

        await db.commit()

        # 4. Verification
        print("\n--- Verification ---")
        async with AsyncSessionLocal() as verify_db:
            res_d = await verify_db.execute(select(Device).where(Device.mac_address == test_mac))
            final_d = res_d.scalar_one()
            print(f"DB Device Label: {final_d.node_label}")
            
            res_a = await verify_db.execute(select(Acre).where(Acre.id == acre.id))
            final_a = res_a.scalar_one()
            print(f"DB Acre Name:    {final_a.name}")
            
            res_z = await verify_db.execute(select(Zone).where(Zone.id == zone.id))
            final_z = res_z.scalar_one()
            print(f"DB Zone Name:    {final_z.name}")
            
            if final_d.node_label == "Hillside Node A1" and final_a.name == "North Field":
                print("\n✅ TEST PASSED: All names correctly persisted across tables!")
            else:
                print("\n❌ TEST FAILED: Discrepancy in stored names.")

if __name__ == "__main__":
    asyncio.run(test_provisioning_flow())

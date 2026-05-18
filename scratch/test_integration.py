import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_full_sync():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("--- PHASE 1: Auth ---")
        reg_payload = {
            "name": "DeepMind Tester",
            "phone": "9999999999",
            "password": "password123",
            "confirm_password": "password123",
            "preferred_lang": "en"
        }
        res = await client.post(f"{BASE_URL}/auth/register", json=reg_payload)
        if res.status_code == 409 or (res.status_code == 400 and "already registered" in res.text):
            print("User already exists, logging in...")
            login_payload = {"identifier": "9999999999", "password": "password123"}
            res = await client.post(f"{BASE_URL}/auth/login", json=login_payload)
        
        print(f"Auth Result: {res.status_code}")
        if res.status_code >= 400:
            print(f"Auth Failed: {res.text}")
            return
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("\n--- PHASE 2: Farm Onboarding ---")
        # 1. Create Farm
        farm_payload = {"name": "AquaFarm V2", "location": "Karnataka", "total_acres": 1}
        res = await client.post(f"{BASE_URL}/farm/setup", json=farm_payload, headers=headers)
        farm_id = res.json()["farm_id"]
        print(f"Farm Created: {farm_id}")

        # 2. Add 1 Acre
        acre_payload = {"farm_id": farm_id, "name": "Acre 1", "soil_type": "Red Soil"}
        res = await client.post(f"{BASE_URL}/farm/acres", json=acre_payload, headers=headers)
        acre_id = res.json()["id"]
        print(f"Acre Created: {acre_id}")

        # 3. Add 1 Zone (Mango)
        zone_payload = {
            "acre_id": acre_id,
            "name": "Mango Orchard",
            "crop_type": "Mango",
            "irrigation_type": "Drip"
        }
        res = await client.post(f"{BASE_URL}/farm/zones", json=zone_payload, headers=headers)
        zone_id = res.json()["id"]
        print(f"Zone Created: {zone_id}")

        # 4. Add 2 Nodes
        for i in range(2):
            node_payload = {
                "mac_address": f"AA:BB:CC:DD:EE:{i+1:02d}",
                "zone_id": zone_id,
                "label": f"Node {i+1}"
            }
            res = await client.post(f"{BASE_URL}/devices/pair", json=node_payload, headers=headers)
            print(f"Node {i+1} Paired: {res.status_code}")

        print("\n--- PHASE 3: Profile Editing ---")
        profile_update = {"name": "DeepMind Master", "preferred_lang": "hi"}
        res = await client.put(f"{BASE_URL}/auth/profile", json=profile_update, headers=headers)
        print(f"Profile Update: {res.status_code}, {res.json()['user']['name']}")

        print("\n--- PHASE 4: Diary & Payment ---")
        diary_payload = {
            "zone_id": zone_id,
            "activity_type": "fertilizer",
            "title": "Applied Organic Compost",
            "body": "Batch #42 applied to orchard.",
            "metadata": {"cost": 1250.50}
        }
        res = await client.post(f"{BASE_URL}/farm/log", json=diary_payload, headers=headers)
        print(f"Diary Log: {res.status_code}, Cost: {diary_payload['metadata']['cost']}")

        print("\n--- PHASE 5: Dashboard Analytics ---")
        res = await client.get(f"{BASE_URL}/dashboard", headers=headers)
        dash = res.json()
        print(f"Dashboard Stats: {dash['total_acres']} Acre, {dash['total_zones']} Zone, {dash['total_nodes']} Nodes")
        
        # Verify operating mode
        if len(dash['zones']) > 0:
            z = dash['zones'][0]
            print(f"Zone '{z['name']}' Mode: {z['operating_mode']}, Root Moisture: {z['estimated_root_moisture']}%")

        print("\n--- PHASE 6: Manual Scheduling ---")
        sched_payload = {
            "label": "Morning Acre Pulse",
            "acre_id": acre_id,
            "time": "06:30",
            "days": ["Mon", "Wed", "Fri"],
            "duration_min": 30,
            "mode": "manual"
        }
        res = await client.post(f"{BASE_URL}/control/schedules", json=sched_payload, headers=headers)
        print(f"Schedule Created: {res.status_code}, Label: {res.json()['label']}")

        print("\n--- INTEGRATION TEST SUCCESSFUL ---")

if __name__ == "__main__":
    asyncio.run(test_full_sync())

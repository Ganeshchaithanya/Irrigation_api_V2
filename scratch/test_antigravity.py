import httpx
import asyncio
import uuid
import json

BASE_URL = "http://localhost:8000/api/v1"

async def run_test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("--- 1. PING ---")
        try:
            res = await client.get(f"{BASE_URL}/auth/ping")
            print(f"Ping: {res.status_code}, {res.json()}")
        except Exception as e:
            print(f"Ping failed: {e}")
            return

        print("\n--- 2. AUTH ---")
        # Try to login first, then register if fails
        login_payload = {"identifier": "9900990099", "password": "password123"}
        res = await client.post(f"{BASE_URL}/auth/login", json=login_payload)
        
        if res.status_code != 200:
            print("Login failed, trying to register admin...")
            reg_payload = {
                "name": "Admin User",
                "phone": "9900990099",
                "password": "password123",
                "confirm_password": "password123",
                "preferred_lang": "en"
            }
            res = await client.post(f"{BASE_URL}/auth/register", json=reg_payload)
            print(f"Register: {res.status_code}")
        
        if res.status_code not in [200, 201]:
            print(f"Auth failed completely: {res.text}")
            return
            
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Auth Successful")

        print("\n--- 3. FARM CREATION ---")
        farm_payload = {
            "name": "Antigravity Test Farm",
            "location": "Virtual Reality",
            "total_acres": 1,
            "zones_per_acre": 1
        }
        res = await client.post(f"{BASE_URL}/farms/farm", json=farm_payload, headers=headers)
        if res.status_code != 201:
            print(f"Farm creation failed: {res.text}")
            return
        
        farm_data = res.json()
        farm_id = farm_data["id"]
        acre_id = farm_data["acres"][0]["id"]
        print(f"Farm Created: {farm_id}, Acre: {acre_id}")

        print("\n--- 4. ZONE CREATION ---")
        zone_payload = {
            "farm_id": farm_id,
            "acre_id": acre_id,
            "name": "Test Zone 1",
            "crop_type": "Digital Wheat",
            "soil_type": "Silicon",
            "irrigation_type": "drip"
        }
        res = await client.post(f"{BASE_URL}/farms/zone", json=zone_payload, headers=headers)
        if res.status_code != 201:
            print(f"Zone creation failed: {res.text}")
            return
        zone_id = res.json()["id"]
        print(f"Zone Created: {zone_id}")

        print("\n--- 5. DEVICE ASSIGNMENT ---")
        master_mac = "AA:BB:CC:DD:EE:FF"
        node_mac = "11:22:33:44:55:66"

        # Assign Master
        master_payload = {
            "mac": master_mac,
            "farm_id": farm_id,
            "node_name": "Antigravity Master"
        }
        res = await client.post("http://localhost:8000/api/assign", json=master_payload)
        print(f"Master Assigned: {res.status_code}")

        # Assign Node to Zone
        node_payload = {
            "mac": node_mac,
            "farm_id": farm_id,
            "zone_id": zone_id,
            "node_name": "Antigravity Node 1"
        }
        res = await client.post("http://localhost:8000/api/assign", json=node_payload)
        print(f"Node Assigned: {res.status_code}")

        print("\n--- 6. SENSOR INGESTION ---")
        ingest_payload = {
            "master_mac": master_mac,
            "flow_rate": 1.2,
            "total_water": 10.5,
            "rain_detected": 0,
            "solar_voltage": 4.2,
            "events": [
                {
                    "node_mac": node_mac,
                    "soil_moisture": 35.5,
                    "temperature": 24.0,
                    "humidity": 55.0,
                    "battery_pct": 92.0,
                    "solar_pct": 10.0,
                    "valve_status": 0
                }
            ]
        }
        res = await client.post(f"{BASE_URL}/sensors", json=ingest_payload)
        print(f"Ingestion Result: {res.status_code}")
        if res.status_code == 200:
            print(f"Response: {res.json()}")

        print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(run_test())

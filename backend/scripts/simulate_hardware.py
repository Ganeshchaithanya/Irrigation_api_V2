import httpx
import json
import time
import random
import os

# Default to local if not specified
API_URL = os.getenv("API_URL", "https://irrigation-api-v2.onrender.com/api/v1")
ADMIN_PHONE = "9449584809"
ADMIN_PASS = "admin@agz2026"

master_mac = "CC:DB:A7:2F:70:E4"
node1_mac = "E0:8C:FE:34:1B:18"
node2_mac = "28:05:A5:25:4D:78"

def run_simulation():
    try:
        # 1. Login
        print(f"Logging in to {API_URL}...")
        login_resp = httpx.post(
            f"{API_URL}/auth/login",
            json={"identifier": ADMIN_PHONE, "password": ADMIN_PASS},
            timeout=30.0
        )
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.text}")
            return
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        print("Login successful!")

        # 2. Get User Profile to get Farm and Zone
        me_resp = httpx.get(f"{API_URL}/auth/me", headers=headers)
        me_data = me_resp.json()
        print(f"Logged in as: {me_data.get('name')}")
        
        # We need to hit a farms endpoint to get the user's farm
        farms_resp = httpx.get(f"{API_URL}/farms", headers=headers)
        farms = farms_resp.json()
        
        if not farms:
            print("No farm found for user! Registering automatically creates one now, but admin user was seeded without one. Let's create one.")
            farm_resp = httpx.post(f"{API_URL}/farms", headers=headers, json={"name": "Auto Farm", "location": "Test", "total_acres": 1})
            farm_id = farm_resp.json()["id"]
            zone_resp = httpx.post(f"{API_URL}/farms/{farm_id}/zones", headers=headers, json={"name": "Auto Zone", "area_acres": 1})
            zone_id = zone_resp.json()["id"]
        else:
            farm_id = farms[0]["id"]
            zones = farms[0].get("zones", [])
            if not zones:
                zone_resp = httpx.post(f"{API_URL}/farms/{farm_id}/zones", headers=headers, json={"name": "Auto Zone", "area_acres": 1})
                zone_id = zone_resp.json()["id"]
            else:
                zone_id = zones[0]["id"]
                
        print(f"Using Farm: {farm_id}")
        print(f"Using Zone: {zone_id}")

        # 3. Discover and Assign Devices
        print("\nDiscovering and Assigning Devices...")
        httpx.post(f"{API_URL}/discover", json={"mac": master_mac, "pairing_code": "MST001", "role": "master"}, timeout=30.0)
        httpx.post(f"{API_URL}/assign/code", headers=headers, json={"pairing_code": "MST001", "farm_id": farm_id, "node_name": "Main Controller"})
        
        httpx.post(f"{API_URL}/discover", json={"mac": node1_mac, "pairing_code": "NOD001", "role": "node"}, timeout=30.0)
        httpx.post(f"{API_URL}/discover", json={"mac": node2_mac, "pairing_code": "NOD002", "role": "node"}, timeout=30.0)

        # Node slots
        slots_resp = httpx.get(f"{API_URL}/farms/zones/{zone_id}/node_slots", headers=headers)
        slots = slots_resp.json()
        if len(slots) < 2:
            s1 = httpx.post(f"{API_URL}/farms/node_slot", headers=headers, json={"zone_id": zone_id, "name": "Slot 1"}).json()
            s2 = httpx.post(f"{API_URL}/farms/node_slot", headers=headers, json={"zone_id": zone_id, "name": "Slot 2"}).json()
            slot1_id = s1["id"]
            slot2_id = s2["id"]
        else:
            slot1_id = slots[0]["id"]
            slot2_id = slots[1]["id"]

        httpx.post(f"{API_URL}/assign/code", headers=headers, json={"pairing_code": "NOD001", "farm_id": farm_id, "zone_id": zone_id, "node_slot_id": slot1_id, "node_name": "Sensor 1"})
        httpx.post(f"{API_URL}/assign/code", headers=headers, json={"pairing_code": "NOD002", "farm_id": farm_id, "zone_id": zone_id, "node_slot_id": slot2_id, "node_name": "Sensor 2"})

        print("\nProvisioning complete. Starting telemetry loop...")
        
        # State variables for simulation
        moisture1 = 80.0
        moisture2 = 78.0
        valve1_status = 0
        valve2_status = 0
        
        while True:
            # Simulate environment changes
            if valve1_status == 1:
                moisture1 += 2.0
            else:
                moisture1 -= 0.5
                
            if valve2_status == 1:
                moisture2 += 2.0
            else:
                moisture2 -= 0.5
                
            # Cap moisture
            moisture1 = min(max(moisture1, 0), 100)
            moisture2 = min(max(moisture2, 0), 100)

            # Build payload
            payload = {
                "masterMac": master_mac,
                "pairingCode": "MST001",
                "batteryPct": 98.5,
                "solarPct": 1.2,
                "solarVoltage": 1.1,
                "rainDetected": 0,
                "flowRate": 15.0 if (valve1_status or valve2_status) else 0.0,
                "totalWater": 150.0,
                "events": [
                    {
                        "nodeMac": node1_mac,
                        "pairingCode": "NOD001",
                        "soilMoisture": moisture1,
                        "temperature": 30.0 + random.uniform(-1, 1),
                        "humidity": 65.0 + random.uniform(-2, 2),
                        "valveStatus": valve1_status,
                        "batteryPct": 97.0,
                        "solarPct": 1.1
                    },
                    {
                        "nodeMac": node2_mac,
                        "pairingCode": "NOD002",
                        "soilMoisture": moisture2,
                        "temperature": 30.5 + random.uniform(-1, 1),
                        "humidity": 64.0 + random.uniform(-2, 2),
                        "valveStatus": valve2_status,
                        "batteryPct": 98.0,
                        "solarPct": 1.1
                    }
                ]
            }
            
            print(f"Sending telemetry -> Node1: {moisture1:.1f}%, Valve1: {valve1_status} | Node2: {moisture2:.1f}%, Valve2: {valve2_status}")
            resp = httpx.post(f"{API_URL}/sensors", json=payload, timeout=30.0)
            
            if resp.status_code == 200:
                data = resp.json()
                # Read valve commands from the AI response!
                cmds = data.get("valve_commands", [])
                for cmd in cmds:
                    if cmd["mac_address"] == node1_mac:
                        valve1_status = 1 if cmd["action"] == "ON" else 0
                        print(f"*** AI commanded Node1 valve: {cmd['action']} ***")
                    elif cmd["mac_address"] == node2_mac:
                        valve2_status = 1 if cmd["action"] == "ON" else 0
                        print(f"*** AI commanded Node2 valve: {cmd['action']} ***")
            else:
                print(f"Failed to send telemetry: {resp.status_code} {resp.text}")
                
            time.sleep(15) # Send every 15 seconds for rapid testing
            
    except Exception as e:
        print(f"Simulation error: {e}")

if __name__ == "__main__":
    run_simulation()

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
        
        # Get farm/zone from dashboard
        dashboard_resp = httpx.get(f"{API_URL}/dashboard", headers=headers, timeout=30.0)
        dashboard = dashboard_resp.json()
        print(f"Dashboard response: {dashboard_resp.status_code}")
        
        farm_id = dashboard.get("farm_id")
        farm_name = dashboard.get("name", "")
        zones = dashboard.get("zones", [])
        
        # If farm is a blank placeholder ("New User"), create a real one
        if not farm_name or farm_name == "New User":
            print("No real farm found. Creating one...")
            farm_create = httpx.post(f"{API_URL}/farms/farm", headers=headers,
                json={"name": "Simulator Farm", "location": "Auto", "total_acres": 1}, timeout=30.0)
            print(f"Farm create: {farm_create.status_code} - {farm_create.text}")
            farm_id = farm_create.json()["id"]
        
        if not zones:
            print("No zone found. Creating one...")
            zone_create = httpx.post(f"{API_URL}/farms/zone", headers=headers,
                json={"farm_id": farm_id, "name": "Zone 1", "crop_type": "Paddy", "soil_type": "Loam", "area_acres": 1}, timeout=30.0)
            print(f"Zone create: {zone_create.status_code} - {zone_create.text}")
            zone_id = zone_create.json()["id"]
        else:
            zone_id = zones[0]["zone_id"]
                
        print(f"Using Farm: {farm_id}")
        print(f"Using Zone: {zone_id}")

        # 3. Discover and Assign Devices
        print("\nDiscovering and Assigning Devices...")
        r = httpx.post(f"{API_URL}/discover", json={"mac": master_mac, "pairing_code": "MST001", "role": "master"}, timeout=30.0)
        print(f"  Discover master: {r.status_code}")
        r = httpx.post(f"{API_URL}/assign/code", headers=headers, json={"pairing_code": "MST001", "farm_id": farm_id, "node_name": "Main Controller"}, timeout=30.0)
        print(f"  Assign master: {r.status_code} - {r.text[:100]}")
        
        r = httpx.post(f"{API_URL}/discover", json={"mac": node1_mac, "pairing_code": "NOD001", "role": "node"}, timeout=30.0)
        print(f"  Discover node1: {r.status_code}")
        r = httpx.post(f"{API_URL}/discover", json={"mac": node2_mac, "pairing_code": "NOD002", "role": "node"}, timeout=30.0)
        print(f"  Discover node2: {r.status_code}")

        # Node slots
        slots_resp = httpx.get(f"{API_URL}/farms/zones/{zone_id}/node_slots", headers=headers, timeout=30.0)
        slots = slots_resp.json()
        print(f"  Node slots found: {len(slots)}")
        if len(slots) < 2:
            s1 = httpx.post(f"{API_URL}/farms/node_slot", headers=headers, json={"zone_id": zone_id, "name": "Slot 1"}, timeout=30.0).json()
            s2 = httpx.post(f"{API_URL}/farms/node_slot", headers=headers, json={"zone_id": zone_id, "name": "Slot 2"}, timeout=30.0).json()
            slot1_id = s1["id"]
            slot2_id = s2["id"]
        else:
            slot1_id = slots[0]["id"]
            slot2_id = slots[1]["id"]
        print(f"  Using slot1={slot1_id}, slot2={slot2_id}")

        r = httpx.post(f"{API_URL}/assign/code", headers=headers, json={"pairing_code": "NOD001", "farm_id": farm_id, "zone_id": zone_id, "node_slot_id": slot1_id, "node_name": "Sensor 1"}, timeout=30.0)
        print(f"  Assign node1: {r.status_code} - {r.text[:100]}")
        r = httpx.post(f"{API_URL}/assign/code", headers=headers, json={"pairing_code": "NOD002", "farm_id": farm_id, "zone_id": zone_id, "node_slot_id": slot2_id, "node_name": "Sensor 2"}, timeout=30.0)
        print(f"  Assign node2: {r.status_code} - {r.text[:100]}")

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
                
            time.sleep(30) # Send every 30 seconds to update readings in db
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Simulation error: {e}")

if __name__ == "__main__":
    run_simulation()

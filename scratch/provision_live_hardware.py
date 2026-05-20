import httpx
import json

api_url = "https://irrigation-api-v2.onrender.com/api/v1"
farm_id = "fd68c71a-f051-4449-a135-bf87a55293cf"
zone_id = "8a924616-f639-46bc-a6dd-1004ccddbd7e"

master_mac = "CC:DB:A7:2F:70:E4"
node1_mac = "E0:8C:FE:34:1B:18"
node2_mac = "28:05:A5:25:4D:78"

try:
    # 1. Login
    print("1. Logging in to live Render backend...")
    login_resp = httpx.post(
        f"{api_url}/auth/login",
        json={"identifier": "chaithanyaug@gmail.com", "password": "password123"},
        timeout=30.0
    )
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        exit()
        
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("Login successful!")

    # 2. Discover Master
    print("\n2. Discovering Master Gateway...")
    disc_master_resp = httpx.post(
        f"{api_url}/discover",
        json={"mac": master_mac, "pairing_code": "MST001", "role": "master"},
        timeout=30.0
    )
    print(f"Status: {disc_master_resp.status_code} - {disc_master_resp.text}")

    # 3. Assign Master Gateway to Farm
    print("\n3. Assigning Master Gateway to Farm...")
    assign_master_resp = httpx.post(
        f"{api_url}/assign/code",
        headers=headers,
        json={
            "pairing_code": "MST001",
            "farm_id": farm_id,
            "zone_id": None,
            "node_slot_id": None,
            "node_name": "Main Controller"
        },
        timeout=30.0
    )
    print(f"Status: {assign_master_resp.status_code} - {assign_master_resp.text}")

    # 4. Discover Nodes
    print("\n4. Discovering Node 1...")
    disc_node1_resp = httpx.post(
        f"{api_url}/discover",
        json={"mac": node1_mac, "pairing_code": "NOD001", "role": "node"},
        timeout=30.0
    )
    print(f"Status: {disc_node1_resp.status_code} - {disc_node1_resp.text}")

    print("\nDiscovering Node 2...")
    disc_node2_resp = httpx.post(
        f"{api_url}/discover",
        json={"mac": node2_mac, "pairing_code": "NOD002", "role": "node"},
        timeout=30.0
    )
    print(f"Status: {disc_node2_resp.status_code} - {disc_node2_resp.text}")

    # 5. Create Node Slots for ZoneA
    print("\n5. Creating Node Slots for ZoneA...")
    slot1_resp = httpx.post(
        f"{api_url}/farms/node_slot",
        headers=headers,
        json={"zone_id": zone_id, "name": "Node Slot 1"},
        timeout=30.0
    )
    print(f"Slot 1 Status: {slot1_resp.status_code} - {slot1_resp.text}")
    slot1_id = slot1_resp.json()["id"]

    slot2_resp = httpx.post(
        f"{api_url}/farms/node_slot",
        headers=headers,
        json={"zone_id": zone_id, "name": "Node Slot 2"},
        timeout=30.0
    )
    print(f"Slot 2 Status: {slot2_resp.status_code} - {slot2_resp.text}")
    slot2_id = slot2_resp.json()["id"]

    # 6. Assign Nodes to Slots
    print("\n6. Assigning Node 1 to Slot 1...")
    assign_node1_resp = httpx.post(
        f"{api_url}/assign/code",
        headers=headers,
        json={
            "pairing_code": "NOD001",
            "farm_id": farm_id,
            "zone_id": zone_id,
            "node_slot_id": slot1_id,
            "node_name": "Sensor Node 1"
        },
        timeout=30.0
    )
    print(f"Status: {assign_node1_resp.status_code} - {assign_node1_resp.text}")

    print("\nAssigning Node 2 to Slot 2...")
    assign_node2_resp = httpx.post(
        f"{api_url}/assign/code",
        headers=headers,
        json={
            "pairing_code": "NOD002",
            "farm_id": farm_id,
            "zone_id": zone_id,
            "node_slot_id": slot2_id,
            "node_name": "Sensor Node 2"
        },
        timeout=30.0
    )
    print(f"Status: {assign_node2_resp.status_code} - {assign_node2_resp.text}")

    # 7. Post Telemetry Sensor Readings
    print("\n7. Ingesting active telemetry reading batch...")
    telemetry_payload = {
        "masterMac": master_mac,
        "pairingCode": "MST001",
        "batteryPct": 98.5,
        "solarPct": 1.2,
        "solarVoltage": 1.1,
        "rainDetected": 0,
        "flowRate": 0.0,
        "totalWater": 150.0,
        "events": [
            {
                "nodeMac": node1_mac,
                "pairingCode": "NOD001",
                "soilMoisture": 100.0,
                "temperature": 31.5,
                "humidity": 63.7,
                "valveStatus": 0,
                "batteryPct": 97.7,
                "solarPct": 1.1
            },
            {
                "nodeMac": node2_mac,
                "pairingCode": "NOD002",
                "soilMoisture": 100.0,
                "temperature": 31.5,
                "humidity": 63.7,
                "valveStatus": 0,
                "batteryPct": 100.0,
                "solarPct": 1.1
            }
        ]
    }
    
    ingest_resp = httpx.post(
        f"{api_url}/sensors",
        json=telemetry_payload,
        timeout=30.0
    )
    print(f"Ingestion Status: {ingest_resp.status_code}")
    if ingest_resp.status_code == 200:
        print(json.dumps(ingest_resp.json(), indent=2))
    else:
        print(ingest_resp.text)

except Exception as e:
    print(f"An error occurred: {e}")

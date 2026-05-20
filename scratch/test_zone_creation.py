import httpx

api_url = "https://irrigation-api-v2.onrender.com/api/v1"

# 1. Log in
print("Attempting login as pre-seeded user...")
try:
    login_resp = httpx.post(
        f"{api_url}/auth/login",
        json={"identifier": "chaithanyaug@gmail.com", "password": "password123"}
    )
    print(f"Login Status: {login_resp.status_code}")
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        exit()
    
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 2. Create a test farm
    print("\nCreating a test farm...")
    farm_resp = httpx.post(
        f"{api_url}/farms/farm",
        headers=headers,
        json={"name": "Diagnostic Farm", "location": "Davangere, Karnataka", "total_acres": 1, "water_source": "Borewell"}
    )
    print(f"Farm Creation Status: {farm_resp.status_code}")
    if farm_resp.status_code not in [200, 201]:
        print(f"Farm creation failed: {farm_resp.text}")
        exit()
        
    farm_data = farm_resp.json()
    farm_id = farm_data["id"]
    acre_id = farm_data["acres"][0]["id"]
    print(f"Created Farm ID: {farm_id}, Acre ID: {acre_id}")
    
    # 3. Create a test zone (matching the exact payload sent by Flutter)
    print("\nAttempting to create zone...")
    zone_payload = {
        "farm_id": farm_id,
        "acre_id": acre_id,
        "name": "ZoneA",
        "crop_type": "Tomato",
        "soil_type": "Loamy",
        "irrigation_type": "Drip",
        "current_stage": "early",
        "weeks_since_sowing": 0,
        "node_slots_count": 2,
        "nodes": []
    }
    
    zone_resp = httpx.post(
        f"{api_url}/farms/zone",
        headers=headers,
        json=zone_payload
    )
    print(f"Zone Creation Status: {zone_resp.status_code}")
    print(f"Zone Creation Response: {zone_resp.text}")

except Exception as e:
    print(f"An error occurred: {e}")

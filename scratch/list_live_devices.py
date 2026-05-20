import httpx
import json

api_url = "https://irrigation-api-v2.onrender.com/api/v1"

try:
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
    
    # 1. Fetch unassigned devices
    print("--- Unassigned Devices ---")
    unassigned_resp = httpx.get(f"{api_url}/unassigned", headers=headers, timeout=30.0)
    print(f"Status: {unassigned_resp.status_code}")
    if unassigned_resp.status_code == 200:
        print(json.dumps(unassigned_resp.json(), indent=2))
    else:
        print(unassigned_resp.text)
        
    # 2. Fetch all zones
    print("\n--- All Zones ---")
    zones_resp = httpx.get(f"{api_url}/zones", headers=headers, timeout=30.0)
    print(f"Status: {zones_resp.status_code}")
    if zones_resp.status_code == 200:
        print(json.dumps(zones_resp.json(), indent=2))
    else:
        print(zones_resp.text)

except Exception as e:
    print(f"An error occurred: {e}")

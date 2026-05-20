import httpx
import json

api_url = "https://irrigation-api-v2.onrender.com/api/v1"
zone_id = "8a924616-f639-46bc-a6dd-1004ccddbd7e"

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
    
    # Fetch detailed zone payload
    print(f"Fetching zone {zone_id}...")
    zone_resp = httpx.get(f"{api_url}/zones/{zone_id}", headers=headers, timeout=30.0)
    print(f"Status: {zone_resp.status_code}")
    if zone_resp.status_code == 200:
        print(json.dumps(zone_resp.json(), indent=2))
    else:
        print(zone_resp.text)

except Exception as e:
    print(f"An error occurred: {e}")

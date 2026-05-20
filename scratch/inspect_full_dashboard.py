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
    
    dash_resp = httpx.get(f"{api_url}/dashboard", headers=headers, timeout=30.0)
    if dash_resp.status_code == 200:
        data = dash_resp.json()
        print("Dashboard JSON:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Dashboard failed: {dash_resp.status_code} - {dash_resp.text}")

except Exception as e:
    print(f"An error occurred: {e}")


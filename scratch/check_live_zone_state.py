import httpx
import json

api_url = "https://irrigation-api-v2.onrender.com/api/v1"

try:
    login_resp = httpx.post(
        f"{api_url}/auth/login",
        json={"identifier": "chaithanyaug@gmail.com", "password": "password123"},
        timeout=30.0
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Let's hit a route or fetch history
    hist_resp = httpx.get(f"{api_url}/sensors/history", headers=headers, timeout=30.0)
    print("--- History ---")
    if hist_resp.status_code == 200:
        print(json.dumps(hist_resp.json()[:2], indent=2))
        
    # Probe analytics or other states
    pnl_resp = httpx.get(f"{api_url}/predictions", headers=headers, timeout=30.0)
    print("\n--- Predictions ---")
    if pnl_resp.status_code == 200:
        print(json.dumps(pnl_resp.json(), indent=2))

except Exception as e:
    print(f"An error occurred: {e}")

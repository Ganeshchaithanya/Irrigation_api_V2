import httpx

api_url = "https://irrigation-api-v2.onrender.com/api/v1"

print("Logging in with 20s timeout...")
try:
    login_resp = httpx.post(
        f"{api_url}/auth/login",
        json={"identifier": "chaithanyaug@gmail.com", "password": "password123"},
        timeout=20.0
    )
    print(f"Login Status: {login_resp.status_code}")
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        exit()
        
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("\nProbing live /dashboard endpoint...")
    dash_resp = httpx.get(f"{api_url}/dashboard", headers=headers, timeout=20.0)
    print(f"Dashboard Response Status: {dash_resp.status_code}")
    # Print first 200 chars of dashboard response
    print(f"Dashboard Content: {dash_resp.text[:500]}...")

except Exception as e:
    print(f"An error occurred: {e}")

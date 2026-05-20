import httpx
import time
import sys

api_url = "https://irrigation-api-v2.onrender.com/api/v1"

print("Logging in...")
try:
    login_resp = httpx.post(
        f"{api_url}/auth/login",
        json={"identifier": "chaithanyaug@gmail.com", "password": "password123"}
    )
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        exit()
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
except Exception as e:
    print(f"Login setup failed: {e}")
    exit()

print("Monitoring live /dashboard endpoint (emojiless). Press Ctrl+C to stop.")
for i in range(1, 10):
    print(f"\n[Attempt {i}] Sending request...")
    start_time = time.time()
    try:
        resp = httpx.get(f"{api_url}/dashboard", headers=headers, timeout=20.0)
        elapsed = time.time() - start_time
        print(f"Response Status: {resp.status_code} | Time: {elapsed:.2f} seconds")
        if resp.status_code == 200:
            print("SUCCESS! The optimized deployment is live and loading instantly!")
            sys.exit(0)
    except httpx.RequestError as exc:
        elapsed = time.time() - start_time
        print(f"Request failed or timed out after {elapsed:.2f} seconds: {exc}")
    
    time.sleep(5)

print("\nMonitoring session finished.")

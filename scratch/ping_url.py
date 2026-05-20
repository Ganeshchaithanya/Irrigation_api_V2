import urllib.request
import json
import time

def ping_backend(url):
    print(f"Pinging URL: {url}")
    start = time.time()
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            status = response.getcode()
            body = response.read().decode('utf-8')
            elapsed = time.time() - start
            print(f"Status Code: {status}")
            print(f"Response Body: {body}")
            print(f"Time Taken: {elapsed:.2f} seconds")
    except Exception as e:
        elapsed = time.time() - start
        print(f"Error pinging backend after {elapsed:.2f}s: {e}")

if __name__ == '__main__':
    ping_backend('https://irrigation-api-v2.onrender.com/api/v1/auth/ping')

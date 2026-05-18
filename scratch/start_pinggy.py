import subprocess
import time
import re

def start_pinggy():
    cmd = ["ssh", "-p", "443", "-o", "StrictHostKeyChecking=no", "-R", "0:localhost:8000", "a.pinggy.io"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    start_time = time.time()
    url = None
    while time.time() - start_time < 30:
        line = process.stdout.readline()
        if not line:
            break
        print(line.strip())
        # Look for https://....pinggy.link or similar
        match = re.search(r'https://[a-zA-Z0-9-]+\.pinggy\.link', line)
        if match:
            url = match.group(0)
            break
        match = re.search(r'https://[a-zA-Z0-9-]+\.a\.pinggy\.io', line)
        if match:
            url = match.group(0)
            break
            
    if url:
        print(f"\nFOUND URL: {url}")
    else:
        print("\nURL NOT FOUND IN 30 SECONDS")
    
    # Keep running
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(line.strip())

if __name__ == "__main__":
    start_pinggy()

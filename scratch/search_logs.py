import json

log_path = r"C:\Users\chait\.gemini\antigravity\brain\c3c49f52-751b-4c85-a864-32244f173ce8\.system_generated\logs\transcript.jsonl"

print("Searching transcript from beginning for hosting references...")
with open(log_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        try:
            data = json.loads(line)
            # Only check user inputs or early model outputs
            step_type = data.get("type", "")
            content = data.get("content", "")
            if not content:
                continue
            
            content_lower = content.lower()
            if "host" in content_lower or "render" in content_lower or "railway" in content_lower or "vercel" in content_lower or "netlify" in content_lower or "git" in content_lower:
                print(f"[{step_type}] Step {i}:")
                print(content[:300] + "...\n")
        except Exception as e:
            pass

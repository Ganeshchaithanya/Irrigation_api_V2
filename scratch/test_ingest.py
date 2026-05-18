import httpx
import asyncio

async def test_post():
    url = "http://localhost:8000/api/v1/sensors"
    payload = {
        "master_mac": "28:05:A5:25:4D:78",
        "battery_pct": 85.5,
        "solar_pct": 45.0,
        "solar_voltage": 12.5,
        "rain_detected": 0,
        "flow_rate": 0.0,
        "total_water": 0.0,
        "events": [
            {
                "node_mac": "E0:8C:FE:34:1B:18",
                "soil_moisture": 45.0,
                "temperature": 25.0,
                "humidity": 60.0,
                "battery_pct": 80.0,
                "solar_pct": 30.0,
                "valve_status": 0
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_post())

import httpx
import asyncio

async def test_owm():
    print("Testing OpenWeatherMap Forecast...")
    url = "https://api.openweathermap.org/data/2.5/forecast?lat=40.71&lon=-74.00&appid=48eae0af422bef1f2c57529d8e1beddf&units=metric"
    resp = await httpx.AsyncClient().get(url)
    print("OWM Forecast:", resp.status_code, resp.text[:100])

async def test_agromonitoring():
    print("Testing AgroMonitoring Weather...")
    url = "http://api.agromonitoring.com/agro/1.0/weather/forecast?lat=40.71&lon=-74.00&appid=48eae0af422bef1f2c57529d8e1beddf"
    resp = await httpx.AsyncClient().get(url)
    print("Agro Forecast:", resp.status_code, resp.text[:100])

async def test_owm_weather():
    print("Testing OpenWeatherMap Current...")
    url = "https://api.openweathermap.org/data/2.5/weather?lat=40.71&lon=-74.00&appid=48eae0af422bef1f2c57529d8e1beddf&units=metric"
    resp = await httpx.AsyncClient().get(url)
    print("OWM Current:", resp.status_code, resp.text[:100])

async def main():
    await test_owm()
    await test_agromonitoring()
    await test_owm_weather()

asyncio.run(main())

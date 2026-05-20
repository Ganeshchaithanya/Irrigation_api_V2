import asyncio
import os
import sys

# Add the workspace root to sys.path so we can import backend packages
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, workspace_root)

from backend.api.device import get_app_version, download_app
from fastapi import HTTPException
from fastapi.responses import FileResponse

async def test_get_app_version():
    print("Testing get_app_version...")
    response = await get_app_version()
    print(f"Response: {response}")
    assert response["version"] == "2.0.0"
    assert response["download_url"] == "https://irrigation-api-v2.onrender.com/api/v1/app/download"
    print("OK - get_app_version test passed successfully!\n")

async def test_download_app():
    print("Testing download_app...")
    # Verify that the APK file exists at the root of the workspace
    apk_path = os.path.join(workspace_root, "app-release.apk")
    print(f"Expected APK path: {apk_path}")
    print(f"APK file exists: {os.path.exists(apk_path)}")
    
    try:
        response = await download_app()
        print(f"Response type: {type(response)}")
        assert isinstance(response, FileResponse)
        assert response.path == apk_path
        assert response.media_type == "application/vnd.android.package-archive"
        assert response.filename == "aquasol-release.apk"
        print("OK - download_app test passed successfully!\n")
    except HTTPException as e:
        print(f"Caught expected/unexpected HTTPException: {e.status_code} - {e.detail}")
        if not os.path.exists(apk_path):
            print("OK - download_app correctly raised 404 since APK file does not exist locally (this is correct behavior!).\n")
        else:
            raise e

async def main():
    print("=== STARTING BACKEND APP ENDPOINTS VERIFICATION ===")
    await test_get_app_version()
    await test_download_app()
    print("=== ALL TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(main())

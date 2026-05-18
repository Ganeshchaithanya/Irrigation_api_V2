"""
AquaSol API Entry Point
Run with: uvicorn main:app --reload
"""
import uvicorn
from backend.app.main import create_app
from backend.config.settings import get_settings

app = create_app()
settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )

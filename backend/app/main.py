"""
FastAPI Application Factory & Middleware
"""
import os
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config.settings import get_settings
from backend.utils.logger import logger

# Import routers
from backend.api.auth import router as auth_router
from backend.api.sensors import router as sensor_router
from backend.api.dashboard import router as dashboard_router
from backend.api.control import router as control_router
from backend.api.chatbot import router as chatbot_router
from backend.api.planner import router as planner_router
from backend.api.reports import router as reports_router
from backend.api.farm import router as farm_router
from backend.api.v1.subsidy import router as subsidy_router
from backend.api.stage import router as stage_router
from backend.api.device import router as device_router
from backend.api.pairing import router as pairing_router
from backend.api.alerts import router as alerts_router
from backend.api.intelligence import router as intelligence_router

# Import startup lifecycle
from backend.app.startup import lifespan


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
    )

    # CORS Policy
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://10.22.57.176:5000",
            "http://10.22.57.176:8000",
            "http://10.22.57.176",
            "http://localhost:3000",
            "http://localhost:5000",
            "http://localhost:8000",
        ],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Request Logger for Debugging
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"[app] {request.method} {request.url.path}")
        response = await call_next(request)
        return response

    # Global Exception Handler
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"[app] Validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "body": str(exc.body)},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"[app] Unhandled exception on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(exc)},
        )

    # Routers
    api_prefix = "/api/v1"
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(sensor_router, prefix=api_prefix)
    app.include_router(dashboard_router, prefix=api_prefix)
    app.include_router(control_router, prefix=api_prefix)
    app.include_router(chatbot_router, prefix=api_prefix)
    app.include_router(planner_router, prefix=api_prefix)
    app.include_router(reports_router, prefix=api_prefix)
    app.include_router(farm_router, prefix=api_prefix)
    app.include_router(subsidy_router, prefix=api_prefix)
    app.include_router(stage_router, prefix=api_prefix)
    app.include_router(device_router, prefix=api_prefix)
    # Master Hardware Compatibility Redirects
    app.include_router(sensor_router, prefix="/api")
    app.include_router(device_router, prefix="/api/device")
    app.include_router(device_router, prefix="/api")
    app.include_router(control_router, prefix="/api")
    app.include_router(control_router, prefix="/api/control")
    
    app.include_router(pairing_router, prefix=api_prefix)
    app.include_router(alerts_router, prefix=api_prefix)
    app.include_router(intelligence_router, prefix=api_prefix)

    # Company-internal admin endpoints (protected by X-Admin-Key header)
    from backend.api.admin import router as admin_router
    app.include_router(admin_router, prefix=api_prefix)

    return app

app = create_app()

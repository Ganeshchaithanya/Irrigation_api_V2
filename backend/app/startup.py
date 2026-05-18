"""
Application Lifespan (Startup / Shutdown)
Loads ML models, connects MQTT, builds E5 RAG index.
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from backend.plugins.ai.anomaly.isolation_forest import load_anomaly_model
from backend.plugins.ai.stage.stage_model import load_stage_models
from backend.plugins.ai.prediction.lstm import load_lstm_model
from backend.plugins.ai.decision.xgboost_engine import load_xgb_models
from backend.plugins.ai.planner.crop_planner import load_planner
from backend.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────
    logger.info("Starting AquaSol API...")

    async def load_models_async():
        try:
            logger.info("Loading AI models in background...")
            import asyncio
            from fastapi.concurrency import run_in_threadpool
            
            # Load heavy models in threadpool to avoid blocking
            await run_in_threadpool(load_anomaly_model)
            await run_in_threadpool(load_stage_models)
            await run_in_threadpool(load_lstm_model)
            await run_in_threadpool(load_xgb_models)
            await run_in_threadpool(load_planner)
            
            logger.info("AI Models Loaded & Ready.")
        except Exception as e:
            logger.error(f"Error loading AI models: {e}")

    # Kick off model loading in background
    import asyncio
    asyncio.create_task(load_models_async())

    # Init MQTT (fast) - DISABLED for HTTP migration
    # logger.info("Initializing MQTT client...")
    # init_mqtt()

    # Start MQTT Bridge listener - DISABLED for HTTP migration
    # from backend.services.mqtt_bridge import mqtt_bridge
    # asyncio.create_task(mqtt_bridge.start_listening())
    
    logger.info("AquaSol API Reachable! (Models loading in background)")
    yield

    # ── Shutdown ───────────────────────────────────────────────────────
    # logger.info("Shutting down AquaSol API...")
    # disconnect()
    logger.info("Shutdown complete.")

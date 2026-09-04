import os
# Restrict multi-threading memory overhead for BLAS/NumPy/SciPy in low-RAM containers
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as api_router
from api.websocket import router as ws_router
from api.delta_routes import router as delta_router
from api.voice_routes import router as voice_router
from database.mongodb import db
from data.websocket import live_feed
from execution.auto_trader import auto_trader
import logging

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("trading_backend")

app = FastAPI(
    title="Hedge-Quant Trading Analyzer Backend API",
    description="High-performance backend API compiling technical indicators, SMC structures, options chains, news sentiment, and Delta Exchange auto-trading.",
    version="2.0.0"
)

# Add CORS Middleware to support front-end dashboard requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    # Trigger database async connection
    await db.connect()
    # Start live feed poller
    await live_feed.start()
    # Start Delta Auto-Trader poller
    auto_trader.start()
    logger.info("FastAPI Backend Server & Auto-Trader started successfully.")

@app.on_event("shutdown")
async def shutdown_db_client():
    # Stop live feed poller
    await live_feed.stop()
    # Stop Delta Auto-Trader poller
    auto_trader.stop()
    logger.info("FastAPI Backend Server & Auto-Trader shut down.")

# Mount routers
app.include_router(api_router)
app.include_router(ws_router)
app.include_router(delta_router)
app.include_router(voice_router)

if __name__ == "__main__":
    logger.info("Initializing Uvicorn ASGI Server...")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)


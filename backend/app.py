import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as api_router
from api.websocket import router as ws_router
from database.mongodb import db
from data.websocket import live_feed
import logging

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("trading_backend")

app = FastAPI(
    title="Hedge-Quant Trading Analyzer Backend API",
    description="High-performance backend API compiling technical indicators, SMC structures, options chains, and news sentiment.",
    version="1.0.0"
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
    logger.info("FastAPI Backend Server started successfully.")

@app.on_event("shutdown")
async def shutdown_db_client():
    # Stop live feed poller
    await live_feed.stop()
    logger.info("FastAPI Backend Server shut down.")

# Mount routers
app.include_router(api_router)
app.include_router(ws_router)

if __name__ == "__main__":
    logger.info("Initializing Uvicorn ASGI Server...")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)

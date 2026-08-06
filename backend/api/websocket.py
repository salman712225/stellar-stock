from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import logging
from data.websocket import live_feed

router = APIRouter()
logger = logging.getLogger("api_websocket")

@router.websocket("/api/ws/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint that streams real-time price updates for the requested asset.
    """
    await websocket.accept()
    queue = asyncio.Queue(maxsize=20)
    
    # Subscribe queue to the live polling feed for this symbol
    await live_feed.subscribe(symbol, queue)
    logger.info(f"Client connected via WebSocket for symbol: {symbol}")
    
    try:
        while True:
            # Wait for the next ticker message from live feed
            ticker_data = await queue.get()
            # Send to the frontend client
            await websocket.send_json(ticker_data)
            queue.task_done()
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from WebSocket for symbol: {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error for {symbol}: {e}")
    finally:
        # Prevent memory leaks by unsubscribing when client leaves
        await live_feed.unsubscribe(symbol, queue)

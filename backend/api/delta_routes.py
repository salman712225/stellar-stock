from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from execution.delta_client import delta_client
from execution.auto_trader import auto_trader

router = APIRouter(prefix="/api/delta", tags=["delta-exchange"])

class DeltaConfigPayload(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    environment: Optional[str] = "testnet" # "testnet", "global", "india"
    asset: Optional[str] = "BTC/USDT"
    timeframe: Optional[str] = "1h"
    instrument_type: Optional[str] = "options" # "options", "futures"
    size_contracts: Optional[int] = 1
    strike_offset: Optional[int] = 0
    stop_loss_pct: Optional[float] = 50.0
    enabled: Optional[bool] = None

class ManualOrderPayload(BaseModel):
    side: str # "BUY", "SELL", "CLOSE"

@router.get("/status")
async def get_delta_status():
    """
    Returns Delta Exchange connection health, balance, and Auto-Trader engine state.
    """
    conn_info = await delta_client.check_connection()
    bot_status = auto_trader.get_status()
    
    return {
        "connection": conn_info,
        "bot": bot_status
    }

@router.post("/config")
async def update_delta_config(payload: DeltaConfigPayload):
    """
    Updates Auto-Trader configuration, credentials, and enabled state.
    """
    cfg = payload.dict(exclude_unset=True)
    status = auto_trader.update_config(cfg)
    return {
        "success": True,
        "status": status,
        "message": "Configuration updated successfully."
    }

@router.get("/positions")
async def get_delta_positions():
    """
    Returns real-time open positions on Delta Exchange with entry price, size, and PnL.
    """
    positions = await delta_client.get_open_positions()
    return {
        "positions": positions,
        "count": len(positions)
    }

@router.get("/balances")
async def get_delta_balances():
    """
    Returns wallet asset balances (USDT, BTC, etc.) and available margin.
    """
    balances = await delta_client.get_wallet_balances()
    return {
        "balances": balances
    }

@router.post("/close-all")
async def panic_close_all():
    """
    Emergency Kill Switch: Liquidates all active positions and pauses the bot.
    """
    result = await auto_trader.panic_close_all()
    return result

@router.post("/manual-order")
async def manual_trigger_order(payload: ManualOrderPayload):
    """
    Triggers a manual Buy Call, Buy Put, or Close order for testing.
    """
    result = await auto_trader.manual_trigger(payload.side)
    return result

@router.get("/logs")
async def get_trade_logs():
    """
    Returns the execution trade logs from the Auto-Trader engine.
    """
    return {
        "logs": auto_trader.logs
    }

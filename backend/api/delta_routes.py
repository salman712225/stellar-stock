from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from execution.delta_client import delta_client, save_persistent_settings, load_persistent_settings
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

@router.get("/settings")
async def get_delta_settings():
    """
    Returns saved settings with masked API secret for security.
    """
    saved = load_persistent_settings()
    masked_secret = ""
    if saved.get("api_secret"):
        sec = saved["api_secret"]
        masked_secret = ("•" * 12) + sec[-4:] if len(sec) > 4 else "••••••••"
        
    return {
        "api_key": saved.get("api_key", ""),
        "api_secret_masked": masked_secret,
        "has_secret": bool(saved.get("api_secret")),
        "environment": saved.get("environment", "testnet"),
        "asset": saved.get("asset", "BTC/USDT"),
        "timeframe": saved.get("timeframe", "1h"),
        "instrument_type": saved.get("instrument_type", "options"),
        "size_contracts": saved.get("size_contracts", 1),
        "strike_offset": saved.get("strike_offset", 0),
        "stop_loss_pct": saved.get("stop_loss_pct", 50.0),
        "enabled": saved.get("enabled", False)
    }

@router.post("/save-settings")
@router.post("/config")
async def update_delta_config(payload: DeltaConfigPayload):
    """
    Updates and permanently saves Delta Exchange API credentials and bot settings.
    """
    cfg = payload.dict(exclude_unset=True)
    status = auto_trader.update_config(cfg)
    conn_info = await delta_client.check_connection()
    
    return {
        "success": True,
        "status": status,
        "connection": conn_info,
        "message": "Settings saved and applied successfully."
    }

@router.post("/test-connection")
async def test_delta_connection():
    """
    Tests credentials against Delta Exchange API and returns connection status.
    """
    conn_info = await delta_client.check_connection()
    balances = await delta_client.get_wallet_balances()
    
    return {
        "connection": conn_info,
        "balances": balances
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


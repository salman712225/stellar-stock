from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio

from execution.snapserve_client import snapserve_voice_client
from data.market_data import market_data_provider
from news.analyzer import sentiment_aggregator
from ai.predictor import market_predictor
from patterns.smc import scan_smc_structure
from indicators.trend import calculate_range_filter
from ai.feature_engineering import build_market_dataframe

router = APIRouter(prefix="/api/voice", tags=["voice"])

class SubscriberRequest(BaseModel):
    name: str
    phone: str
    assets: Optional[List[str]] = ["ALL"]
    enabled: Optional[bool] = True

class TestCallRequest(BaseModel):
    phone: str
    asset: Optional[str] = "BTC/USDT"
    signal: Optional[str] = "BUY"
    timeframe: Optional[str] = "1h"

class VoiceSettingsRequest(BaseModel):
    api_key: Optional[str] = None
    agent_id: Optional[int] = None
    base_url: Optional[str] = None

@router.get("/status")
async def get_voice_status():
    """
    Returns SnapServe AI Voice status, wallet balance, active phone numbers, and agent info.
    """
    wallet = await snapserve_voice_client.get_wallet_balance()
    phone_numbers = await snapserve_voice_client.get_phone_numbers()
    agents = await snapserve_voice_client.list_agents()
    subscribers = snapserve_voice_client.get_subscribers()

    current_agent = None
    for a in agents:
        if a.get("id") == snapserve_voice_client.agent_id:
            current_agent = a
            break

    return {
        "status": "connected" if "balanceCents" in wallet else "error",
        "wallet": wallet,
        "agent_id": snapserve_voice_client.agent_id,
        "agent": current_agent,
        "phone_numbers": phone_numbers,
        "subscribers_count": len(subscribers),
        "active_subscribers_count": len([s for s in subscribers if s.get("enabled", True)])
    }

@router.get("/subscribers")
async def get_subscribers():
    """
    Returns the list of registered VIP traders / customers subscribed to automated voice signals.
    """
    return snapserve_voice_client.get_subscribers()

@router.post("/subscribers")
async def add_or_update_subscriber(req: SubscriberRequest):
    """
    Adds or updates a subscriber phone number for voice trading alerts.
    """
    if not req.phone or len(req.phone.strip()) < 8:
        raise HTTPException(status_code=400, detail="Invalid phone number format. Include country code e.g. +919876543210")
    
    result = snapserve_voice_client.add_subscriber(
        name=req.name,
        phone=req.phone,
        assets=req.assets,
        enabled=req.enabled if req.enabled is not None else True
    )
    return result

@router.delete("/subscribers/{phone}")
async def remove_subscriber(phone: str):
    """
    Removes a subscriber phone number.
    """
    success = snapserve_voice_client.remove_subscriber(phone)
    if not success:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"success": True, "message": f"Subscriber {phone} removed successfully"}

@router.post("/test-call")
async def trigger_test_call(req: TestCallRequest):
    """
    Triggers an instant live AI voice call with comprehensive market insights to the provided phone number.
    """
    if not req.phone or len(req.phone.strip()) < 8:
        raise HTTPException(status_code=400, detail="Please provide a valid destination phone number with country code (e.g. +919876543210)")

    asset = req.asset or "BTC/USDT"
    signal = req.signal.upper() if req.signal else "BUY"
    timeframe = req.timeframe or "1h"

    # 1. Gather live market data & insights for the chosen asset
    df = await market_data_provider.get_data(asset, timeframe, limit=50)
    spot_price = float(df["close"].iloc[-1]) if not df.empty else (65000.0 if "BTC" in asset else 3400.0)
    
    # 2. Enrich technicals & levels
    atr = spot_price * 0.02
    if not df.empty:
        df_en = build_market_dataframe(df)
        if "atr_14" in df_en:
            atr = float(df_en["atr_14"].iloc[-1])

    if signal == "BUY":
        stop_loss = round(spot_price - (2.0 * atr), 2)
        tp1 = round(spot_price + (1.5 * atr), 2)
        tp2 = round(spot_price + (3.0 * atr), 2)
        tp3 = round(spot_price + (5.0 * atr), 2)
    else:
        stop_loss = round(spot_price + (2.0 * atr), 2)
        tp1 = round(spot_price - (1.5 * atr), 2)
        tp2 = round(spot_price - (3.0 * atr), 2)
        tp3 = round(spot_price - (5.0 * atr), 2)

    # 3. Sentiment & News
    sentiment_data = await sentiment_aggregator.analyze_market_sentiment(asset)
    sentiment_score = sentiment_data.get("overall_score", 0.0)
    sentiment_label = sentiment_data.get("overall_label", "Bullish")
    articles = sentiment_data.get("news_articles", [])
    top_headline = articles[0].get("title") if articles else "Crypto and stock markets consolidate ahead of economic releases"

    # 4. SMC Insights
    smc_data = scan_smc_structure(df) if not df.empty else {}
    unmit_ob = len([ob for ob in smc_data.get("order_blocks", []) if not ob.get("mitigated")])
    smc_summary = f"{unmit_ob} unmitigated order blocks, liquidity footprint aligned with {signal}"

    # 5. AI Prediction
    prediction = await market_predictor.get_prediction(df_en if not df.empty else df, asset, sentiment_score)
    ai_pred_str = f"{prediction.get('signal')} ({prediction.get('confidence', 0.5):.0%} confidence)"

    signal_payload = {
        "asset": asset,
        "signal": signal,
        "timeframe": timeframe,
        "spot_price": spot_price,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "fear_greed": f"{'Greed' if sentiment_score > 0.1 else 'Fear' if sentiment_score < -0.1 else 'Neutral'} (Score: {sentiment_score})",
        "smc_summary": smc_summary,
        "ai_prediction": ai_pred_str,
        "top_news": top_headline,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    # Dispatch outbound call
    result = await snapserve_voice_client.trigger_outbound_call(req.phone, signal_payload)
    return result

@router.get("/calls")
async def get_recent_calls(limit: int = 15):
    """
    Returns recent call transcripts, recordings, durations, and AI summaries from SnapServe.
    """
    calls = await snapserve_voice_client.get_call_history(limit)
    return calls

@router.post("/settings")
async def save_voice_settings(req: VoiceSettingsRequest):
    """
    Updates SnapServe API key, default Agent ID, or base URL.
    """
    settings = {}
    if req.api_key:
        settings["api_key"] = req.api_key
    if req.agent_id:
        settings["agent_id"] = req.agent_id
    if req.base_url:
        settings["base_url"] = req.base_url

    success = snapserve_voice_client.save_settings(settings)
    return {"success": success, "message": "Voice settings saved successfully"}

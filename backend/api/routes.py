from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import pandas as pd
import asyncio

from data.market_data import market_data_provider
from data.options_data import options_data_provider
from indicators.volume import calculate_volume_profile, add_volume_indicators
from indicators.fibonacci import calculate_fibonacci_levels
from patterns.smc import scan_smc_structure
from news.analyzer import sentiment_aggregator
from ai.predictor import market_predictor
from ai.train import train_model
from ai.llm_reasoning import llm_reasoner
from backtest.engine import BacktestEngine
from backtest.strategy import SMCMomentumStrategy
from backtest.metrics import calculate_backtest_metrics

import math
import numpy as np
from typing import Any

def clean_json_data(obj: Any) -> Any:
    """
    Recursively replaces NaN, Inf, and -Inf with None (null) in nested structures.
    """
    if isinstance(obj, dict):
        return {k: clean_json_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json_data(x) for x in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.generic):
        val = obj.item()
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val
    return obj

router = APIRouter()

# Input schemas
class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    risk_percent: float = 1.0
    leverage: float = 1.0
    risk_reward_ratio: float = 2.0
    initial_capital: float = 10000.0

class TrainRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"

class PositionEvaluationRequest(BaseModel):
    symbol: str
    position_type: str  # "long", "short", "call", "put"
    entry_price: float
    limit_price: float
    stop_loss: float
    strike: Optional[float] = None
    timeframe: str = "1h"

@router.get("/api/analyze")
async def analyze_symbol(symbol: str, timeframe: str = "1h", limit: int = 200):
    """
    Run complete market analysis for a symbol: indicators, SMC, sentiment, ML, and LLM reasoning.
    """
    # 1. Fetch OHLCV
    df = await market_data_provider.get_data(symbol, timeframe, limit)
    if df.empty:
        raise HTTPException(status_code=400, detail=f"Could not retrieve market data for {symbol}")

    # 2. Options chain (if F&O stock/index)
    options_data = None
    is_crypto = "/" in symbol or symbol.endswith("USDT")
    if not is_crypto:
        options_data = await options_data_provider.fetch_options_chain(symbol)
        if not options_data:
            options_data = None

    # 3. Sentiment & News
    sentiment_data = await sentiment_aggregator.analyze_market_sentiment(symbol)
    sentiment_score = sentiment_data.get("overall_score", 0.0)

    # 4. Indicators & SMC
    # Enrich data for technicals & patterns
    from ai.feature_engineering import build_market_dataframe
    df_enriched = build_market_dataframe(df)
    
    # Volume Profile & Fibonacci
    poc, vah, val = calculate_volume_profile(df)
    fib_levels, fib_trend = calculate_fibonacci_levels(df)
    
    # SMC Scanner
    smc_data = scan_smc_structure(df)

    # 5. ML Predictor
    prediction = await market_predictor.get_prediction(df_enriched, symbol, sentiment_score, options_data)

    # 6. LLM Reasoning Report
    latest_close = float(df["close"].iloc[-1])
    latest_indicators = {
        "rsi_14": float(df_enriched["rsi_14"].iloc[-1]),
        "direction": int(df_enriched["direction"].iloc[-1]),
        "ema_9": float(df_enriched["ema_9"].iloc[-1]),
        "ema_21": float(df_enriched["ema_21"].iloc[-1]),
        "macd_hist": float(df_enriched["macd_hist"].iloc[-1]),
        "adx": float(df_enriched["adx"].iloc[-1]),
        "atr_14": float(df_enriched["atr_14"].iloc[-1]) if "atr_14" in df_enriched else None,
        "range_direction": int(df_enriched["range_direction"].iloc[-1]) if "range_direction" in df_enriched else 1
    }
    
    latest_patterns = {
        "doji": bool(df_enriched["pattern_doji"].iloc[-1]),
        "hammer": bool(df_enriched["pattern_hammer"].iloc[-1]),
        "shooting_star": bool(df_enriched["pattern_shooting_star"].iloc[-1]),
        "bullish_engulfing": bool(df_enriched["pattern_bullish_engulfing"].iloc[-1]),
        "bearish_engulfing": bool(df_enriched["pattern_bearish_engulfing"].iloc[-1]),
        "harami": bool(df_enriched["pattern_harami"].iloc[-1])
    }

    report_task = llm_reasoner.generate_report(
        symbol=symbol,
        price=latest_close,
        indicators=latest_indicators,
        patterns=latest_patterns,
        smc=smc_data,
        options=options_data,
        sentiment=sentiment_data,
        prediction=prediction
    )
    
    report = await report_task

    # Convert DataFrame to JSON serializable list of dicts
    chart_candles = df_enriched.tail(100).to_dict(orient="records")

    return clean_json_data({
        "symbol": symbol,
        "timeframe": timeframe,
        "current_price": latest_close,
        "indicators": {
            "volume_profile": {"poc": poc, "vah": vah, "val": val},
            "fibonacci": {"levels": fib_levels, "trend": fib_trend},
            "latest": latest_indicators
        },
        "smc": {
            "order_blocks": smc_data["order_blocks"][-10:], # last 10
            "bos": smc_data["bos"][-10:],
            "choch": smc_data["choch"][-10:],
            "fvgs": smc_data["fvgs"][-15:]
        },
        "patterns": latest_patterns,
        "sentiment": {
            "score": sentiment_score,
            "label": sentiment_data["overall_label"],
            "news_summary": sentiment_data["news_summary"],
            "reddit_summary": sentiment_data["reddit_summary"],
            "twitter_summary": sentiment_data["twitter_summary"],
            "articles": sentiment_data["news_articles"][:5],
            "reddit_posts": sentiment_data["reddit_posts"][:5],
            "tweets": sentiment_data["tweets"][:5]
        },
        "prediction": prediction,
        "report": report,
        "chart_data": chart_candles
    })

@router.get("/api/options-chain")
async def get_options_chain(symbol: str, expiry: Optional[int] = None):
    """
    Retrieve options chain and calculated Greeks/metrics for a given ticker index/stock.
    """
    is_crypto = "/" in symbol or symbol.endswith("USDT")
    if is_crypto:
        raise HTTPException(status_code=400, detail="Options chains are only available for F&O Stocks/Indices (e.g. AAPL, SPY, ^NSEI)")
        
    chain = await options_data_provider.fetch_options_chain(symbol)
    if not chain:
        raise HTTPException(status_code=404, detail=f"No options chain data available for {symbol}")
    return clean_json_data(chain)

@router.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    """
    Run an event-driven backtesting strategy and get equity metrics.
    """
    df = await market_data_provider.get_data(req.symbol, req.timeframe, limit=500)
    if df.empty:
        raise HTTPException(status_code=400, detail=f"Could not load data for backtest: {req.symbol}")

    # Prepare technical indicators and SMC structures
    from ai.feature_engineering import build_market_dataframe
    df_enriched = build_market_dataframe(df)
    smc_data = scan_smc_structure(df)

    # Get recent average news sentiment for the strategy
    sentiment_data = await sentiment_aggregator.analyze_market_sentiment(req.symbol)
    sentiment_score = sentiment_data.get("overall_score", 0.0)

    # Instantiate strategy and run engine
    strategy = SMCMomentumStrategy()
    engine = BacktestEngine(initial_capital=req.initial_capital)
    
    result = engine.run_backtest(
        df=df_enriched,
        strategy=strategy,
        smc_data=smc_data,
        sentiment_score=sentiment_score,
        risk_percent=req.risk_percent,
        leverage=req.leverage,
        risk_reward_ratio=req.risk_reward_ratio
    )
    
    # Calculate performance metrics
    metrics = calculate_backtest_metrics(result["trades"], result["equity_curve"], req.initial_capital)

    return clean_json_data({
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "initial_capital": req.initial_capital,
        "final_capital": result["final_capital"],
        "metrics": metrics,
        "trades": result["trades"][-100:],  # return last 100 trades
        "equity_curve": result["equity_curve"]
    })

@router.post("/api/train-model")
async def trigger_model_training(req: TrainRequest, background_tasks: BackgroundTasks):
    """
    Trigger ML model training for a symbol in the background.
    """
    # Load 500 rows
    df = await market_data_provider.get_data(req.symbol, req.timeframe, limit=500)
    if df.empty:
        raise HTTPException(status_code=400, detail=f"Could not fetch training data for {req.symbol}")
        
    from ai.feature_engineering import build_market_dataframe
    df_enriched = build_market_dataframe(df)
    
    sentiment_data = await sentiment_aggregator.analyze_market_sentiment(req.symbol)
    sentiment_score = sentiment_data.get("overall_score", 0.0)

    options_data = None
    is_crypto = "/" in req.symbol or req.symbol.endswith("USDT")
    if not is_crypto:
        options_data = await options_data_provider.fetch_options_chain(req.symbol)
        
    # Run train_model synchronously or defer in background tasks
    return clean_json_data(result)

@router.post("/api/evaluate-position")
async def api_evaluate_position(req: PositionEvaluationRequest):
    """
    Evaluate an active trade position (Greeks, roadblocks, sentiment, ML align)
    and provide action recommendation.
    """
    df = await market_data_provider.get_data(req.symbol, req.timeframe, limit=200)
    if df.empty:
        raise HTTPException(status_code=400, detail=f"Failed to fetch market data for {req.symbol}")
        
    spot_price = float(df["close"].iloc[-1])
    
    from ai.feature_engineering import build_market_dataframe
    df_enriched = build_market_dataframe(df)
    
    # Options data if applicable
    options_data = None
    is_crypto = "/" in req.symbol or req.symbol.endswith("USDT")
    if not is_crypto and req.position_type.lower() in ["call", "put"]:
        options_data = await options_data_provider.fetch_options_chain(req.symbol)

    # Sentiment & News
    sentiment_data = await sentiment_aggregator.analyze_market_sentiment(req.symbol)
    sentiment_score = sentiment_data.get("overall_score", 0.0)

    # SMC Scanner
    smc_data = scan_smc_structure(df)

    # ML Predictor
    prediction = await market_predictor.get_prediction(df_enriched, req.symbol, sentiment_score, options_data)
    
    from risk.evaluator import evaluate_position
    evaluation = evaluate_position(
        symbol=req.symbol,
        position_type=req.position_type,
        entry_price=req.entry_price,
        limit_price=req.limit_price,
        stop_loss=req.stop_loss,
        spot_price=spot_price,
        strike=req.strike,
        df_enriched=df_enriched,
        smc_data=smc_data,
        options_chain=options_data,
        sentiment_score=sentiment_score,
        prediction=prediction
    )
    return clean_json_data(evaluation)

@router.get("/api/signals-scan")
async def scan_range_filter_signals():
    """
    Lightweight scan checking Range Filter buy/sell triggers
    across all default crypto and traditional equity index assets.
    """
    from datetime import datetime, timezone
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "DOT/USDT", "^NSEI", "^NSEBANK", "RELIANCE.NS", "AAPL", "SPY", "QQQ"]
    results = []
    
    async def scan_single(symbol: str):
        try:
            df = await market_data_provider.get_data(symbol, "1h", limit=35)
            if df.empty or len(df) < 20:
                return None
            
            from indicators.trend import calculate_range_filter
            rf_df = calculate_range_filter(df)
            
            last_row = rf_df.iloc[-1]
            prev_row = rf_df.iloc[-2] if len(rf_df) >= 2 else last_row
            
            signal = None
            price = float(last_row["close"])
            
            if last_row["range_buy"] or prev_row["range_buy"]:
                signal = "BUY"
            elif last_row["range_sell"] or prev_row["range_sell"]:
                signal = "SELL"
                
            if signal:
                return {
                    "symbol": symbol,
                    "signal": signal,
                    "price": price,
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
                }
        except Exception:
            pass
        return None
        
    tasks = [scan_single(sym) for sym in symbols]
    scanned = await asyncio.gather(*tasks)
    return clean_json_data([s for s in scanned if s])


import gc
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import pandas as pd
import asyncio
import math
import numpy as np
from datetime import datetime, timezone

from data.market_data import market_data_provider
from data.options_data import options_data_provider
from indicators.volume import calculate_volume_profile, add_volume_indicators
from indicators.fibonacci import calculate_fibonacci_levels
from indicators.trend import calculate_pivot_points
from patterns.smc import scan_smc_structure
from news.analyzer import sentiment_aggregator
from ai.predictor import market_predictor
from ai.train import train_model
from ai.llm_reasoning import llm_reasoner
from backtest.engine import BacktestEngine
from backtest.strategy import SMCMomentumStrategy
from backtest.metrics import calculate_backtest_metrics

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

class AICopilotRequest(BaseModel):
    symbol: str
    question: str
    context: Optional[Dict[str, Any]] = None

@router.get("/api/market-overview")
async def get_market_overview():
    """
    Returns real-time ticker overview for BTC, ETH, XAUT, SOL, XRP.
    """
    overview = await market_data_provider.get_market_overview()
    return clean_json_data(overview)

@router.get("/api/analyze")
async def analyze_symbol(symbol: str, timeframe: str = "1h", limit: int = 200):
    """
    Run complete market analysis for a symbol: all indicators, SMC, sentiment, ML, and LLM reasoning.
    """
    # 1. Fetch OHLCV
    df = await market_data_provider.get_data(symbol, timeframe, limit)
    if df.empty:
        raise HTTPException(status_code=400, detail=f"Could not retrieve market data for {symbol}")

    # 2. Options chain (if F&O stock/index)
    options_data = None
    is_crypto = "/" in symbol or symbol.endswith("USDT") or symbol in ["BTC", "ETH", "XAUT", "SOL", "XRP"]
    if not is_crypto:
        options_data = await options_data_provider.fetch_options_chain(symbol)

    # 3. Sentiment & News
    sentiment_data = await sentiment_aggregator.analyze_market_sentiment(symbol)
    sentiment_score = sentiment_data.get("overall_score", 0.0)

    # 4. Indicators & SMC
    from ai.feature_engineering import build_market_dataframe
    df_enriched = build_market_dataframe(df)
    
    # Volume Profile & Fibonacci & Pivot Points
    poc, vah, val, vol_dist = calculate_volume_profile(df)
    fib_levels, fib_trend = calculate_fibonacci_levels(df)
    pivot_levels = calculate_pivot_points(df)
    
    # SMC Scanner
    smc_data = scan_smc_structure(df)

    # 5. ML Predictor
    prediction = await market_predictor.get_prediction(df_enriched, symbol, sentiment_score, options_data)

    # 6. Extract Latest Indicators Map
    latest_close = float(df["close"].iloc[-1])
    last_row = df_enriched.iloc[-1]
    
    latest_indicators = {
        # Trend
        "sma_20": float(last_row.get("sma_20", latest_close)),
        "sma_50": float(last_row.get("sma_50", latest_close)),
        "sma_100": float(last_row.get("sma_100", latest_close)),
        "sma_200": float(last_row.get("sma_200", latest_close)),
        "ema_9": float(last_row.get("ema_9", latest_close)),
        "ema_21": float(last_row.get("ema_21", latest_close)),
        "ema_50": float(last_row.get("ema_50", latest_close)),
        "ema_200": float(last_row.get("ema_200", latest_close)),
        "hma_20": float(last_row.get("hma_20", latest_close)),
        "macd": float(last_row.get("macd", 0.0)),
        "macd_signal": float(last_row.get("macd_signal", 0.0)),
        "macd_hist": float(last_row.get("macd_hist", 0.0)),
        "adx": float(last_row.get("adx", 0.0)),
        "plus_di": float(last_row.get("plus_di", 0.0)),
        "minus_di": float(last_row.get("minus_di", 0.0)),
        "supertrend": float(last_row.get("supertrend", latest_close)),
        "direction": int(last_row.get("direction", 1)),
        "range_filter": float(last_row.get("range_filter", latest_close)),
        "range_direction": int(last_row.get("range_direction", 1)),
        "ichimoku_tenkan": float(last_row.get("ichimoku_tenkan", latest_close)),
        "ichimoku_kijun": float(last_row.get("ichimoku_kijun", latest_close)),
        "ichimoku_cloud": str(last_row.get("ichimoku_cloud", "bullish")),
        "parabolic_sar": float(last_row.get("parabolic_sar", latest_close)),
        
        # Momentum
        "rsi_14": float(last_row.get("rsi_14", 50.0)),
        "rsi_7": float(last_row.get("rsi_7", 50.0)),
        "stoch_k": float(last_row.get("stoch_k", 50.0)),
        "stoch_d": float(last_row.get("stoch_d", 50.0)),
        "stoch_rsi_k": float(last_row.get("stoch_rsi_k", 50.0)),
        "stoch_rsi_d": float(last_row.get("stoch_rsi_d", 50.0)),
        "williams_r": float(last_row.get("williams_r", -50.0)),
        "mfi_14": float(last_row.get("mfi_14", 50.0)),
        "ultimate_oscillator": float(last_row.get("ultimate_oscillator", 50.0)),
        "roc_12": float(last_row.get("roc_12", 0.0)),
        "cci_20": float(last_row.get("cci_20", 0.0)),
        "bullish_divergence": bool(last_row.get("bullish_divergence", False)),
        "bearish_divergence": bool(last_row.get("bearish_divergence", False)),
        
        # Volatility
        "bb_upper": float(last_row.get("bb_upper", latest_close)),
        "bb_middle": float(last_row.get("bb_middle", latest_close)),
        "bb_lower": float(last_row.get("bb_lower", latest_close)),
        "bb_pct_b": float(last_row.get("bb_pct_b", 0.5)),
        "bb_bandwidth": float(last_row.get("bb_bandwidth", 5.0)),
        "bb_squeeze": bool(last_row.get("bb_squeeze", False)),
        "atr_14": float(last_row.get("atr_14", latest_close * 0.02)),
        "natr_14": float(last_row.get("natr_14", 2.0)),
        "kc_upper": float(last_row.get("kc_upper", latest_close)),
        "kc_middle": float(last_row.get("kc_middle", latest_close)),
        "kc_lower": float(last_row.get("kc_lower", latest_close)),
        "dc_upper": float(last_row.get("dc_upper", latest_close)),
        "dc_middle": float(last_row.get("dc_middle", latest_close)),
        "dc_lower": float(last_row.get("dc_lower", latest_close)),
        
        # Volume
        "obv": float(last_row.get("obv", 0.0)),
        "vwap": float(last_row.get("vwap", latest_close)),
        "vwap_upper_1": float(last_row.get("vwap_upper_1", latest_close)),
        "vwap_lower_1": float(last_row.get("vwap_lower_1", latest_close)),
        "vwap_upper_2": float(last_row.get("vwap_upper_2", latest_close)),
        "vwap_lower_2": float(last_row.get("vwap_lower_2", latest_close)),
        "cmf_20": float(last_row.get("cmf_20", 0.0)),
        "ad_line": float(last_row.get("ad_line", 0.0)),
        "vol_sma_20": float(last_row.get("vol_sma_20", 0.0)),
        "vol_spike": bool(last_row.get("vol_spike", False))
    }
    
    latest_patterns = {
        "doji": bool(last_row.get("pattern_doji", False)),
        "hammer": bool(last_row.get("pattern_hammer", False)),
        "inverted_hammer": bool(last_row.get("pattern_inverted_hammer", False)),
        "shooting_star": bool(last_row.get("pattern_shooting_star", False)),
        "bullish_engulfing": bool(last_row.get("pattern_bullish_engulfing", False)),
        "bearish_engulfing": bool(last_row.get("pattern_bearish_engulfing", False)),
        "morning_star": bool(last_row.get("pattern_morning_star", False)),
        "evening_star": bool(last_row.get("pattern_evening_star", False)),
        "harami": bool(last_row.get("pattern_harami", False)),
        "three_white_soldiers": bool(last_row.get("pattern_three_white_soldiers", False)),
        "three_black_crows": bool(last_row.get("pattern_three_black_crows", False))
    }

    # 7. LLM Reasoning Report
    report_task = llm_reasoner.generate_report(
        symbol=symbol,
        price=latest_close,
        indicators=latest_indicators,
        patterns=latest_patterns,
        smc=smc_data,
        options=options_data,
        sentiment=sentiment_data,
        prediction=prediction,
        pivots=pivot_levels
    )
    report = await report_task

    chart_candles = df_enriched.tail(120).to_dict(orient="records")

    # Fear & Greed approximation from sentiment & RSI
    fear_greed_score = int(np.clip(50 + (sentiment_score * 30) + ((latest_indicators["rsi_14"] - 50) * 0.4), 5, 95))
    fear_greed_label = "Extreme Greed" if fear_greed_score >= 75 else "Greed" if fear_greed_score >= 55 else "Extreme Fear" if fear_greed_score <= 25 else "Fear" if fear_greed_score <= 45 else "Neutral"

    response_payload = clean_json_data({
        "symbol": symbol,
        "timeframe": timeframe,
        "current_price": latest_close,
        "indicators": {
            "volume_profile": {
                "poc": poc, 
                "vah": vah, 
                "val": val,
                "distribution": vol_dist
            },
            "fibonacci": {"levels": fib_levels, "trend": fib_trend},
            "pivots": pivot_levels,
            "latest": latest_indicators
        },
        "smc": {
            "order_blocks": smc_data.get("order_blocks", [])[-10:],
            "bos": smc_data.get("bos", [])[-10:],
            "choch": smc_data.get("choch", [])[-10:],
            "fvgs": smc_data.get("fvgs", [])[-15:]
        },
        "patterns": latest_patterns,
        "sentiment": {
            "score": sentiment_score,
            "label": sentiment_data["overall_label"],
            "fear_greed": {
                "score": fear_greed_score,
                "label": fear_greed_label
            },
            "news_summary": sentiment_data["news_summary"],
            "reddit_summary": sentiment_data["reddit_summary"],
            "twitter_summary": sentiment_data["twitter_summary"],
            "articles": sentiment_data["news_articles"][:10],
            "reddit_posts": sentiment_data["reddit_posts"][:6],
            "tweets": sentiment_data["tweets"][:6]
        },
        "prediction": prediction,
        "report": report,
        "chart_data": chart_candles
    })

    # Explicit memory cleanup
    del df, df_enriched, smc_data, sentiment_data, chart_candles
    gc.collect()

    return response_payload

@router.post("/api/ai-copilot")
async def ai_copilot_chat(req: AICopilotRequest):
    """
    Interactive AI Copilot providing strategy recommendations and answers.
    """
    context = req.context or {}
    if not context.get("current_price"):
        # Fetch lightweight snapshot if context missing
        df = await market_data_provider.get_data(req.symbol, "1h", limit=50)
        if not df.empty:
            from ai.feature_engineering import build_market_dataframe
            df_en = build_market_dataframe(df)
            context["current_price"] = float(df["close"].iloc[-1])
            context["indicators"] = {"latest": {"rsi_14": float(df_en["rsi_14"].iloc[-1]), "direction": int(df_en["direction"].iloc[-1])}}
            
    answer = await llm_reasoner.answer_copilot_query(
        symbol=req.symbol,
        question=req.question,
        context=context
    )
    return clean_json_data({"answer": answer})

@router.get("/api/multi-timeframe")
async def get_multi_timeframe(symbol: str):
    """
    Evaluates confluence across 5m, 15m, 1h, 4h, 1d timeframes.
    """
    timeframes = ["5m", "15m", "1h", "4h", "1d"]
    tf_data = await market_data_provider.fetch_multi_timeframe(symbol, timeframes)
    
    confluence = {}
    bullish_votes = 0
    bearish_votes = 0
    
    for tf, df in tf_data.items():
        if df.empty or len(df) < 20:
            continue
        from ai.feature_engineering import build_market_dataframe
        df_en = build_market_dataframe(df)
        last = df_en.iloc[-1]
        
        rsi = float(last.get("rsi_14", 50))
        st_dir = int(last.get("direction", 1))
        macd_h = float(last.get("macd_hist", 0))
        rf_dir = int(last.get("range_direction", 1))
        
        # Calculate TF score (-100 to +100)
        score = 0
        score += 30 if st_dir == 1 else -30
        score += 25 if rf_dir == 1 else -25
        score += 25 if rsi > 50 else -25
        score += 20 if macd_h > 0 else -20
        
        bias = "BULLISH" if score > 20 else "BEARISH" if score < -20 else "NEUTRAL"
        if bias == "BULLISH": bullish_votes += 1
        elif bias == "BEARISH": bearish_votes += 1
        
        confluence[tf] = {
            "price": float(last["close"]),
            "bias": bias,
            "score": score,
            "rsi": round(rsi, 1),
            "supertrend": "Bullish" if st_dir == 1 else "Bearish"
        }
        
    total_valid = max(1, len(confluence))
    bull_pct = round((bullish_votes / total_valid) * 100, 1)
    overall_confluence = "STRONG BULLISH" if bull_pct >= 80 else "BULLISH" if bull_pct >= 60 else "STRONG BEARISH" if bull_pct <= 20 else "BEARISH" if bull_pct <= 40 else "CONSOLIDATING"
    
    del tf_data
    gc.collect()

    return clean_json_data({
        "symbol": symbol,
        "overall_confluence": overall_confluence,
        "bullish_percentage": bull_pct,
        "matrix": confluence
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

    from ai.feature_engineering import build_market_dataframe
    df_enriched = build_market_dataframe(df)
    smc_data = scan_smc_structure(df)

    sentiment_data = await sentiment_aggregator.analyze_market_sentiment(req.symbol)
    sentiment_score = sentiment_data.get("overall_score", 0.0)

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
    
    metrics = calculate_backtest_metrics(result["trades"], result["equity_curve"], req.initial_capital)

    return clean_json_data({
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "initial_capital": req.initial_capital,
        "final_capital": result["final_capital"],
        "metrics": metrics,
        "trades": result["trades"][-100:],
        "equity_curve": result["equity_curve"]
    })

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
    
    options_data = None
    is_crypto = "/" in req.symbol or req.symbol.endswith("USDT")
    if not is_crypto and req.position_type.lower() in ["call", "put"]:
        options_data = await options_data_provider.fetch_options_chain(req.symbol)

    sentiment_data = await sentiment_aggregator.analyze_market_sentiment(req.symbol)
    sentiment_score = sentiment_data.get("overall_score", 0.0)

    smc_data = scan_smc_structure(df)
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
    Lightweight scan checking Range Filter buy/sell triggers across crypto and traditional assets.
    """
    symbols = ["BTC/USDT", "ETH/USDT", "XAUT/USDT", "SOL/USDT", "XRP/USDT", "AAPL", "SPY", "QQQ"]
    
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
    result = clean_json_data([s for s in scanned if s])
    del tasks, scanned
    gc.collect()
    return result



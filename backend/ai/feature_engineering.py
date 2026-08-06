import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any
from indicators.trend import add_trend_indicators
from indicators.momentum import add_momentum_indicators
from indicators.volatility import add_volatility_indicators
from indicators.volume import add_volume_indicators
from patterns.candlestick import detect_candlestick_patterns

def build_market_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies all indicators and candlestick pattern detection
    to build a fully enriched DataFrame.
    Idempotent check prevents duplicate column generation.
    """
    if "sma_20" in df.columns and "rsi_14" in df.columns and "supertrend" in df.columns:
        return df

    d = df.copy()
    d = add_trend_indicators(d)
    d = add_momentum_indicators(d)
    d = add_volatility_indicators(d)
    d = add_volume_indicators(d)
    d = detect_candlestick_patterns(d)
    return d

def extract_features(
    df: pd.DataFrame, 
    sentiment_score: float = 0.0,
    options_metrics: Optional[Dict[str, Any]] = None
) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    """
    Engineers ML-ready features from the enriched DataFrame.
    Includes technicals, lags, candle shapes, options metrics, and sentiment.
    Returns: X (DataFrame of features), y (Series of targets - or None if predicting live)
    """
    if df.empty or len(df) < 50:
        return pd.DataFrame(), None

    d = build_market_dataframe(df)
    
    # 1. Feature Engineering
    features = pd.DataFrame(index=d.index)
    
    # Technical features
    features["rsi_14"] = d["rsi_14"].fillna(50)
    features["cci_20"] = d["cci_20"].fillna(0)
    features["adx"] = d["adx"].fillna(25)
    features["plus_di"] = d["plus_di"].fillna(20)
    features["minus_di"] = d["minus_di"].fillna(20)
    
    # Moving Average ratios
    features["close_to_sma20"] = (d["close"] / d["sma_20"].fillna(d["close"])) - 1.0
    features["close_to_sma50"] = (d["close"] / d["sma_50"].fillna(d["close"])) - 1.0
    features["close_to_sma200"] = (d["close"] / d["sma_200"].fillna(d["close"])) - 1.0
    features["ema9_to_ema21"] = (d["ema_9"] / d["ema_21"].fillna(d["ema_9"])) - 1.0
    
    # MACD
    features["macd_hist"] = d["macd_hist"].fillna(0)
    features["macd_signal"] = d["macd_signal"].fillna(0)
    
    # Bollinger Bands Position
    bb_width = (d["bb_upper"] - d["bb_lower"]) / d["bb_middle"]
    features["bb_width"] = bb_width.fillna(0.05)
    bb_pct = (d["close"] - d["bb_lower"]) / (d["bb_upper"] - d["bb_lower"] + 1e-10)
    features["bb_pct"] = bb_pct.fillna(0.5)
    
    # Volatility Ratio
    features["atr_ratio"] = (d["atr_14"] / d["close"]).fillna(0.02)
    
    # Volume indicator CMF
    features["cmf_20"] = d["cmf_20"].fillna(0)
    
    # Lags (Returns over last 1, 2, 5 periods)
    features["return_1"] = d["close"].pct_change(1).fillna(0)
    features["return_2"] = d["close"].pct_change(2).fillna(0)
    features["return_5"] = d["close"].pct_change(5).fillna(0)
    
    # Candlestick patterns (convert True/False to 1/0)
    features["pattern_doji"] = d["pattern_doji"].astype(int)
    features["pattern_hammer"] = d["pattern_hammer"].astype(int)
    features["pattern_shooting_star"] = d["pattern_shooting_star"].astype(int)
    features["pattern_bullish_engulfing"] = d["pattern_bullish_engulfing"].astype(int)
    features["pattern_bearish_engulfing"] = d["pattern_bearish_engulfing"].astype(int)
    features["pattern_harami"] = d["pattern_harami"].astype(int)
    
    # Sentiment score (injected from news/social analyzer)
    features["sentiment_score"] = sentiment_score
    
    # Options Chain features (if available)
    if options_metrics:
        pcr_oi = options_metrics.get("pcr_oi", 1.0)
        pcr_vol = options_metrics.get("pcr_volume", 1.0)
        max_pain = options_metrics.get("max_pain", d["close"].iloc[-1])
        underlying = options_metrics.get("underlying_price", d["close"].iloc[-1])
        
        features["opt_pcr_oi"] = pcr_oi
        features["opt_pcr_vol"] = pcr_vol
        features["opt_max_pain_dist"] = (max_pain / underlying) - 1.0
    else:
        features["opt_pcr_oi"] = 1.0
        features["opt_pcr_vol"] = 1.0
        features["opt_max_pain_dist"] = 0.0

    # 2. Define Target (1 if next close > current close, else 0)
    # Target only generated if not running live prediction (i.e. we are training)
    # We shift close backwards by 1 to get the next close
    y = (d["close"].shift(-1) > d["close"]).astype(int)
    # Remove last row for training since it won't have a future target
    
    return features, y

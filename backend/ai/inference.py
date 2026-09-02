import pickle
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from config import MODEL_DIR
from ai.feature_engineering import extract_features

logger = logging.getLogger("ai_inference")

def predict_latest(
    df: pd.DataFrame, 
    symbol: str,
    sentiment_score: float = 0.0,
    options_metrics: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Predict price direction (UP/DOWN) for the next candle.
    If no trained model is found, defaults to a technical indicator consensus algorithm.
    """
    if df.empty or len(df) < 30:
        return {"signal": "HOLD", "confidence": 0.5, "method": "fallback (insufficient data)"}

    clean_symbol = symbol.replace("/", "_").replace("^", "IDX_")
    model_path = MODEL_DIR / f"{clean_symbol}_rf.pkl"
    
    # 1. Attempt ML Inference
    if model_path.exists():
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
                
            # Extract features for the entire dataframe
            X, _ = extract_features(df, sentiment_score, options_metrics)
            if X.empty:
                raise ValueError("Feature matrix empty")

            # Predict on the last row (current candle)
            last_row = X.iloc[[-1]].fillna(0)
            
            # Align features with model if needed
            if hasattr(model, "feature_names_in_"):
                # If mismatch in feature columns, retrain or reindex
                missing = [c for c in model.feature_names_in_ if c not in last_row.columns]
                extra = [c for c in last_row.columns if c not in model.feature_names_in_]
                if missing or extra:
                    last_row = last_row.reindex(columns=model.feature_names_in_, fill_value=0)
            
            # Predict probability
            prob = model.predict_proba(last_row)[0] # e.g. [prob_down, prob_up]
            up_prob = float(prob[1])
            
            if up_prob >= 0.55:
                signal = "BUY"
                confidence = up_prob
            elif up_prob <= 0.45:
                signal = "SELL"
                confidence = 1.0 - up_prob
            else:
                signal = "HOLD"
                confidence = 0.5
                
            return {
                "signal": signal,
                "confidence": round(confidence, 3),
                "method": "random_forest_ml",
                "up_probability": round(up_prob, 3)
            }
        except Exception as e:
            logger.error(f"Error running ML inference for {symbol}: {e}. Falling back to technical rules.")

    # 2. Heuristic Indicator Consensus Fallback
    # (Triggers if model pkl is not trained yet or errors)
    try:
        from indicators.trend import add_trend_indicators
        from indicators.momentum import add_momentum_indicators
        
        d = df.copy()
        if "direction" not in d.columns:
            d = add_trend_indicators(d)
        if "rsi_14" not in d.columns:
            d = add_momentum_indicators(d)
        
        last_row = d.iloc[-1]
        
        rsi_val = float(last_row.get("rsi_14", 50.0))
        direction_val = int(last_row.get("direction", 1))
        macd_hist_val = float(last_row.get("macd_hist", 0.0))
        
        score = 0
        if direction_val == 1:
            score += 1
        else:
            score -= 1
            
        if rsi_val > 50:
            score += 1
        elif rsi_val < 50:
            score -= 1
            
        if macd_hist_val > 0:
            score += 1
        elif macd_hist_val < 0:
            score -= 1
            
        if sentiment_score >= 0.15:
            score += 1
        elif sentiment_score <= -0.15:
            score -= 1

        if score >= 2:
            signal = "BUY"
            confidence = 0.5 + (score * 0.1)
        elif score <= -2:
            signal = "SELL"
            confidence = 0.5 + (abs(score) * 0.1)
        else:
            signal = "HOLD"
            confidence = 0.5
            
        return {
            "signal": signal,
            "confidence": round(min(0.95, confidence), 2),
            "method": "technical_consensus_fallback",
            "consensus_score": score
        }
    except Exception as e:
        logger.error(f"Fallback algorithm failed: {e}")
        return {"signal": "HOLD", "confidence": 0.5, "method": "fallback (error)"}

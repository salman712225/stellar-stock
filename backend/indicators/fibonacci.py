import pandas as pd
import numpy as np
from typing import Dict, Tuple

def calculate_fibonacci_levels(df: pd.DataFrame, lookback: int = 100) -> Tuple[Dict[str, float], str]:
    """
    Find recent swing highs and lows in the lookback window
    and calculate Fibonacci Retracement levels.
    Returns: (Dict of levels, trend string)
    """
    if df.empty or len(df) < 10:
        return {}, "unknown"
        
    recent_df = df.tail(lookback)
    
    # Identify index of maximum and minimum prices
    max_idx = recent_df["high"].idxmax()
    min_idx = recent_df["low"].idxmin()
    
    high_val = float(recent_df.loc[max_idx, "high"])
    low_val = float(recent_df.loc[min_idx, "low"])
    diff = high_val - low_val
    
    if diff == 0:
        return {
            "0.0": high_val,
            "0.236": high_val,
            "0.382": high_val,
            "0.500": high_val,
            "0.618": high_val,
            "0.786": high_val,
            "1.000": high_val
        }, "flat"

    # If the low happened before the high, we are in an uptrend (retracing from high to low)
    if min_idx < max_idx:
        trend = "uptrend"
        levels = {
            "0.0": high_val,
            "0.236": high_val - 0.236 * diff,
            "0.382": high_val - 0.382 * diff,
            "0.500": high_val - 0.500 * diff,
            "0.618": high_val - 0.618 * diff,
            "0.786": high_val - 0.786 * diff,
            "1.000": low_val
        }
    else:
        # If high happened before low, we are in a downtrend (retracing from low to high)
        trend = "downtrend"
        levels = {
            "0.0": low_val,
            "0.236": low_val + 0.236 * diff,
            "0.382": low_val + 0.382 * diff,
            "0.500": low_val + 0.500 * diff,
            "0.618": low_val + 0.618 * diff,
            "0.786": low_val + 0.786 * diff,
            "1.000": high_val
        }
        
    return levels, trend

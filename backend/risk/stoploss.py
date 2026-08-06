import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_atr_stoploss(
    entry_price: float,
    atr_value: float,
    direction: str = "long",
    multiplier: float = 2.0
) -> float:
    """ATR-based Stop Loss calculation."""
    if direction.lower() == "long":
        return entry_price - (multiplier * atr_value)
    else:
        return entry_price + (multiplier * atr_value)

def calculate_swing_stoploss(
    df: pd.DataFrame,
    direction: str = "long",
    lookback: int = 15,
    buffer_pct: float = 0.1
) -> float:
    """Swing High/Low based Stop Loss calculation."""
    recent = df.tail(lookback)
    if direction.lower() == "long":
        # Stop loss below lowest low of lookback period
        lowest_low = recent["low"].min()
        return lowest_low * (1.0 - buffer_pct / 100.0)
    else:
        # Stop loss above highest high of lookback period
        highest_high = recent["high"].max()
        return highest_high * (1.0 + buffer_pct / 100.0)

def calculate_structural_stoploss(
    entry_price: float,
    levels: List[float],
    direction: str = "long",
    buffer_pct: float = 0.15
) -> float:
    """
    Stop Loss placed just below the nearest support (for longs)
    or just above the nearest resistance (for shorts).
    """
    if not levels:
        # Fallback to simple % stop loss
        return entry_price * 0.98 if direction.lower() == "long" else entry_price * 1.02

    sorted_levels = sorted(levels)
    
    if direction.lower() == "long":
        # Find nearest support below entry price
        supports = [lvl for lvl in sorted_levels if lvl < entry_price]
        if supports:
            nearest_support = supports[-1]
            return nearest_support * (1.0 - buffer_pct / 100.0)
        else:
            return entry_price * 0.98
    else:
        # Find nearest resistance above entry price
        resistances = [lvl for lvl in sorted_levels if lvl > entry_price]
        if resistances:
            nearest_resistance = resistances[0]
            return nearest_resistance * (1.0 + buffer_pct / 100.0)
        else:
            return entry_price * 1.02

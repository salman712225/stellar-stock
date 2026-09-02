import pandas as pd
import numpy as np

def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect multiple candlestick patterns in the DataFrame.
    Adds Boolean columns for each pattern:
    - 'pattern_doji'
    - 'pattern_hammer'
    - 'pattern_shooting_star'
    - 'pattern_bullish_engulfing'
    - 'pattern_bearish_engulfing'
    - 'pattern_morning_star'
    - 'pattern_evening_star'
    - 'pattern_harami'
    """
    d = df.copy()
    
    # Pre-calculate sizes
    close = d["close"]
    open_p = d["open"]
    high = d["high"]
    low = d["low"]
    
    body_size = (close - open_p).abs()
    candle_range = high - low
    is_bullish = close > open_p
    is_bearish = close < open_p
    
    upper_wick = np.where(is_bullish, high - close, high - open_p)
    lower_wick = np.where(is_bullish, open_p - low, close - low)
    
    # 1. Doji: Body size is less than 10% of the entire candle range
    d["pattern_doji"] = (body_size <= (0.10 * candle_range)) & (candle_range > 0)
    
    # 2. Hammer: Lower wick is at least 2x the body, upper wick is small (< 10% of range), bullish or neutral
    d["pattern_hammer"] = (
        (lower_wick >= 2 * body_size) & 
        (upper_wick <= 0.10 * candle_range) & 
        (body_size > 0) &
        is_bullish
    )
    
    # 3. Shooting Star: Upper wick is at least 2x the body, lower wick is small (< 10% of range), bearish
    d["pattern_shooting_star"] = (
        (upper_wick >= 2 * body_size) & 
        (lower_wick <= 0.10 * candle_range) & 
        (body_size > 0) &
        is_bearish
    )
    
    # Shifted values for multi-candle patterns
    prev_close = close.shift(1)
    prev_open = open_p.shift(1)
    prev_is_bearish = prev_close < prev_open
    prev_is_bullish = prev_close > prev_open
    prev_body_size = (prev_close - prev_open).abs()
    
    # 4. Bullish Engulfing: Previous is bearish, current is bullish, and current body engulfs previous body
    d["pattern_bullish_engulfing"] = (
        prev_is_bearish & 
        is_bullish & 
        (open_p <= prev_close) & 
        (close >= prev_open) &
        (body_size > prev_body_size)
    )
    
    # 5. Bearish Engulfing: Previous is bullish, current is bearish, and current body engulfs previous body
    d["pattern_bearish_engulfing"] = (
        prev_is_bullish & 
        is_bearish & 
        (open_p >= prev_close) & 
        (close <= prev_open) &
        (body_size > prev_body_size)
    )
    
    # 6. Harami: Current body is inside previous body
    d["pattern_harami"] = (
        (body_size < prev_body_size) &
        (
            ((open_p > prev_close) & (close < prev_open) & prev_is_bearish & is_bullish) |
            ((open_p < prev_close) & (close > prev_open) & prev_is_bullish & is_bearish)
        )
    )
    
    # 3-candle shifted values
    prev2_close = close.shift(2)
    prev2_open = open_p.shift(2)
    prev2_is_bearish = prev2_close < prev2_open
    prev2_is_bullish = prev2_close > prev2_open
    
    # 7. Morning Star: Candle 2 is bearish, 1 is small (doji/spinning top), 0 is bullish and closes past midpoint of 2
    # In shifted indexes: prev2 is bearish, prev1 is small body, current is bullish
    midpoint_prev2 = prev2_open - (prev2_open - prev2_close) / 2
    d["pattern_morning_star"] = (
        prev2_is_bearish &
        (prev_body_size <= 0.20 * (high.shift(1) - low.shift(1))) &
        is_bullish &
        (close > midpoint_prev2)
    )
    
    # 9. Inverted Hammer: Upper wick >= 2x body, lower wick small, bullish or neutral
    d["pattern_inverted_hammer"] = (
        (upper_wick >= 2 * body_size) &
        (lower_wick <= 0.10 * candle_range) &
        (body_size > 0) &
        is_bullish
    )

    # 10. Three White Soldiers: 3 consecutive bullish candles with progressive higher closes and opens within previous body
    d["pattern_three_white_soldiers"] = (
        is_bullish &
        prev_is_bullish &
        prev2_is_bullish &
        (close > prev_close) &
        (prev_close > prev2_close) &
        (open_p > prev_open) &
        (open_p < prev_close)
    )

    # 11. Three Black Crows: 3 consecutive bearish candles with progressive lower closes
    d["pattern_three_black_crows"] = (
        is_bearish &
        prev_is_bearish &
        prev2_is_bearish &
        (close < prev_close) &
        (prev_close < prev2_close) &
        (open_p < prev_open) &
        (open_p > prev_close)
    )

    return d


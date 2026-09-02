import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

def calculate_sma(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    """Calculate Simple Moving Average."""
    return df[column].rolling(window=period).mean()

def calculate_ema(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    """Calculate Exponential Moving Average."""
    return df[column].ewm(span=period, adjust=False).mean()

def calculate_wma(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    """Calculate Weighted Moving Average."""
    weights = np.arange(1, period + 1)
    def wma_calc(series):
        return np.dot(series, weights) / weights.sum()
    return df[column].rolling(window=period).apply(wma_calc, raw=True)

def calculate_hma(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
    """Calculate Hull Moving Average (HMA)."""
    half_length = int(period / 2)
    sqrt_length = int(np.sqrt(period))
    wma_half = calculate_wma(df, half_length, column)
    wma_full = calculate_wma(df, period, column)
    diff = 2 * wma_half - wma_full
    diff_df = pd.DataFrame({"close": diff}, index=df.index)
    return calculate_wma(diff_df, sqrt_length, "close")

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, column: str = "close") -> pd.DataFrame:
    """
    Calculate MACD, MACD Signal, and MACD Histogram.
    """
    fast_ema = calculate_ema(df, fast, column)
    slow_ema = calculate_ema(df, slow, column)
    macd = fast_ema - slow_ema
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    
    return pd.DataFrame({
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist
    }, index=df.index)

def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate ADX (Average Directional Index) along with +DI and -DI.
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    
    up_move = high - prev_high
    down_move = prev_low - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    smoothed_plus_dm = pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean()
    smoothed_minus_dm = pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean()
    
    plus_di = 100 * (smoothed_plus_dm / (atr + 1e-10))
    minus_di = 100 * (smoothed_minus_dm / (atr + 1e-10))
    
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10).abs())
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    return pd.DataFrame({
        "adx": adx,
        "plus_di": plus_di,
        "minus_di": minus_di
    }, index=df.index)

def calculate_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0) -> pd.DataFrame:
    """
    Calculate Supertrend indicator.
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()

    hl2 = (high + low) / 2
    basic_ub = hl2 + (multiplier * atr)
    basic_lb = hl2 - (multiplier * atr)
    
    final_ub = basic_ub.copy()
    final_lb = basic_lb.copy()
    supertrend = pd.Series(0.0, index=df.index)
    direction = pd.Series(1, index=df.index)
    
    for i in range(1, len(df)):
        if basic_ub.iloc[i] < final_ub.iloc[i-1] or close.iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]
            
        if basic_lb.iloc[i] > final_lb.iloc[i-1] or close.iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]
            
        if supertrend.iloc[i-1] == final_ub.iloc[i-1]:
            if close.iloc[i] > final_ub.iloc[i]:
                supertrend.iloc[i] = final_lb.iloc[i]
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = final_ub.iloc[i]
                direction.iloc[i] = -1
        else:
            if close.iloc[i] < final_lb.iloc[i]:
                supertrend.iloc[i] = final_ub.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = final_lb.iloc[i]
                direction.iloc[i] = 1
                
    return pd.DataFrame({
        "supertrend": supertrend,
        "direction": direction,
        "long_band": final_lb,
        "short_band": final_ub
    }, index=df.index)

def calculate_range_filter(df: pd.DataFrame, period: int = 14, multiplier: float = 1.5) -> pd.DataFrame:
    """
    Calculate Range Filter indicator (TradingView Range Filter Buy/Sell).
    """
    close = df["close"]
    price_change = (close - close.shift(1)).abs()
    price_change.iloc[0] = 0.0
    range_size = price_change.ewm(span=period, adjust=False).mean() * multiplier
    
    filter_val = close.copy()
    
    for i in range(1, len(df)):
        prev_filt = filter_val.iloc[i-1]
        curr_close = close.iloc[i]
        curr_range = range_size.iloc[i]
        
        if curr_close > prev_filt:
            filter_val.iloc[i] = max(prev_filt, curr_close - curr_range)
        elif curr_close < prev_filt:
            filter_val.iloc[i] = min(prev_filt, curr_close + curr_range)
        else:
            filter_val.iloc[i] = prev_filt
            
    direction = pd.Series(0, index=df.index)
    buy_signal = pd.Series(False, index=df.index)
    sell_signal = pd.Series(False, index=df.index)
    
    for i in range(1, len(df)):
        prev_dir = direction.iloc[i-1]
        curr_close = close.iloc[i]
        curr_filt = filter_val.iloc[i]
        
        if curr_close > curr_filt:
            direction.iloc[i] = 1
            if prev_dir != 1:
                buy_signal.iloc[i] = True
        elif curr_close < curr_filt:
            direction.iloc[i] = -1
            if prev_dir != -1:
                sell_signal.iloc[i] = True
        else:
            direction.iloc[i] = prev_dir
            
    return pd.DataFrame({
        "range_filter": filter_val,
        "range_direction": direction,
        "range_buy": buy_signal,
        "range_sell": sell_signal
    }, index=df.index)

def calculate_ichimoku_cloud(df: pd.DataFrame, conv_period: int = 9, base_period: int = 26, span_b_period: int = 52) -> pd.DataFrame:
    """
    Calculate Ichimoku Kinko Hyo Cloud components:
    - Tenkan-sen (Conversion Line)
    - Kijun-sen (Base Line)
    - Senkou Span A (Leading Span A)
    - Senkou Span B (Leading Span B)
    - Chikou Span (Lagging Span)
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    tenkan_sen = (high.rolling(window=conv_period).max() + low.rolling(window=conv_period).min()) / 2.0
    
    # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    kijun_sen = (high.rolling(window=base_period).max() + low.rolling(window=base_period).min()) / 2.0
    
    # Senkou Span A (Leading Span A): (Conversion Line + Base Line) / 2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2.0).shift(base_period)
    
    # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2
    senkou_span_b = ((high.rolling(window=span_b_period).max() + low.rolling(window=span_b_period).min()) / 2.0).shift(base_period)
    
    # Chikou Span (Lagging Span): Close shifted back 26 periods
    chikou_span = close.shift(-base_period)
    
    # Cloud state
    cloud_color = np.where(senkou_span_a > senkou_span_b, "bullish", "bearish")
    
    return pd.DataFrame({
        "ichimoku_tenkan": tenkan_sen,
        "ichimoku_kijun": kijun_sen,
        "ichimoku_span_a": senkou_span_a,
        "ichimoku_span_b": senkou_span_b,
        "ichimoku_chikou": chikou_span,
        "ichimoku_cloud": cloud_color
    }, index=df.index)

def calculate_parabolic_sar(df: pd.DataFrame, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.20) -> pd.Series:
    """
    Calculate Parabolic Stop and Reverse (SAR).
    """
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    length = len(df)
    
    sar = np.zeros(length)
    if length < 2:
        return pd.Series(sar, index=df.index)
        
    is_bullish = close[1] >= close[0]
    ep = high[0] if is_bullish else low[0]
    af = af_start
    sar[0] = low[0] if is_bullish else high[0]
    
    for i in range(1, length):
        prev_sar = sar[i-1]
        if is_bullish:
            current_sar = prev_sar + af * (ep - prev_sar)
            current_sar = min(current_sar, low[i-1], low[i-2] if i > 1 else low[i-1])
            
            if low[i] < current_sar:
                is_bullish = False
                sar[i] = ep
                ep = low[i]
                af = af_start
            else:
                sar[i] = current_sar
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            current_sar = prev_sar + af * (ep - prev_sar)
            current_sar = max(current_sar, high[i-1], high[i-2] if i > 1 else high[i-1])
            
            if high[i] > current_sar:
                is_bullish = True
                sar[i] = ep
                ep = high[i]
                af = af_start
            else:
                sar[i] = current_sar
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)
                    
    return pd.Series(sar, index=df.index)

def calculate_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate Pivot Points (Standard, Fibonacci, Camarilla) from recent high/low/close.
    """
    if len(df) < 2:
        return {}
        
    recent_high = float(df["high"].tail(20).max())
    recent_low = float(df["low"].tail(20).min())
    recent_close = float(df["close"].iloc[-1])
    
    # Standard Pivot
    pp = (recent_high + recent_low + recent_close) / 3.0
    r1 = (2 * pp) - recent_low
    s1 = (2 * pp) - recent_high
    r2 = pp + (recent_high - recent_low)
    s2 = pp - (recent_high - recent_low)
    r3 = recent_high + 2 * (pp - recent_low)
    s3 = recent_low - 2 * (recent_high - pp)
    
    # Fibonacci Pivots
    range_hl = recent_high - recent_low
    fib_r3 = pp + (range_hl * 1.000)
    fib_r2 = pp + (range_hl * 0.618)
    fib_r1 = pp + (range_hl * 0.382)
    fib_s1 = pp - (range_hl * 0.382)
    fib_s2 = pp - (range_hl * 0.618)
    fib_s3 = pp - (range_hl * 1.000)
    
    # Camarilla Pivots
    cam_r4 = recent_close + range_hl * 1.1 / 2.0
    cam_r3 = recent_close + range_hl * 1.1 / 4.0
    cam_r2 = recent_close + range_hl * 1.1 / 6.0
    cam_r1 = recent_close + range_hl * 1.1 / 12.0
    cam_s1 = recent_close - range_hl * 1.1 / 12.0
    cam_s2 = recent_close - range_hl * 1.1 / 6.0
    cam_s3 = recent_close - range_hl * 1.1 / 4.0
    cam_s4 = recent_close - range_hl * 1.1 / 2.0
    
    return {
        "standard": {
            "pivot": round(pp, 4),
            "r1": round(r1, 4), "r2": round(r2, 4), "r3": round(r3, 4),
            "s1": round(s1, 4), "s2": round(s2, 4), "s3": round(s3, 4)
        },
        "fibonacci": {
            "pivot": round(pp, 4),
            "r1": round(fib_r1, 4), "r2": round(fib_r2, 4), "r3": round(fib_r3, 4),
            "s1": round(fib_s1, 4), "s2": round(fib_s2, 4), "s3": round(fib_s3, 4)
        },
        "camarilla": {
            "r4": round(cam_r4, 4), "r3": round(cam_r3, 4), "r2": round(cam_r2, 4), "r1": round(cam_r1, 4),
            "s1": round(cam_s1, 4), "s2": round(cam_s2, 4), "s3": round(cam_s3, 4), "s4": round(cam_s4, 4)
        }
    }

def add_trend_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all trend indicators to the DataFrame."""
    d = df.copy()
    d["sma_20"] = calculate_sma(d, 20)
    d["sma_50"] = calculate_sma(d, 50)
    d["sma_100"] = calculate_sma(d, 100)
    d["sma_200"] = calculate_sma(d, 200)
    
    d["ema_9"] = calculate_ema(d, 9)
    d["ema_21"] = calculate_ema(d, 21)
    d["ema_50"] = calculate_ema(d, 50)
    d["ema_100"] = calculate_ema(d, 100)
    d["ema_200"] = calculate_ema(d, 200)
    d["hma_20"] = calculate_hma(d, 20)
    
    macd_df = calculate_macd(d)
    d = pd.concat([d, macd_df], axis=1)
    
    adx_df = calculate_adx(d)
    d = pd.concat([d, adx_df], axis=1)
    
    st_df = calculate_supertrend(d)
    d = pd.concat([d, st_df], axis=1)
    
    rf_df = calculate_range_filter(d)
    d = pd.concat([d, rf_df], axis=1)
    
    ichimoku_df = calculate_ichimoku_cloud(d)
    d = pd.concat([d, ichimoku_df], axis=1)
    
    d["parabolic_sar"] = calculate_parabolic_sar(d)
    return d


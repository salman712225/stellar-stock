import pandas as pd
import numpy as np

def calculate_sma(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    """Calculate Simple Moving Average."""
    return df[column].rolling(window=period).mean()

def calculate_ema(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    """Calculate Exponential Moving Average."""
    return df[column].ewm(span=period, adjust=False).mean()

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, column: str = "close") -> pd.DataFrame:
    """
    Calculate MACD, MACD Signal, and MACD Histogram.
    Returns a DataFrame with 'macd', 'macd_signal', and 'macd_hist'.
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
    try:
        # Fallback to pandas_ta
        import pandas_ta as ta
        adx_df = ta.adx(df["high"], df["low"], df["close"], length=period)
        if adx_df is not None:
            return pd.DataFrame({
                "adx": adx_df.iloc[:, 0],
                "plus_di": adx_df.iloc[:, 1],
                "minus_di": adx_df.iloc[:, 2]
            }, index=df.index)
    except Exception:
        pass

    # Direct implementation if pandas_ta fails
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    
    # DM+ and DM-
    up_move = high - prev_high
    down_move = prev_low - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    # True Range (TR)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Smoothed TR, +DM, -DM
    atr = tr.rolling(window=period).mean() # simple moving average for simplicity
    smoothed_plus_dm = pd.Series(plus_dm, index=df.index).rolling(window=period).mean()
    smoothed_minus_dm = pd.Series(minus_dm, index=df.index).rolling(window=period).mean()
    
    plus_di = 100 * (smoothed_plus_dm / atr)
    minus_di = 100 * (smoothed_minus_dm / atr)
    
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).abs())
    adx = dx.rolling(window=period).mean()
    
    return pd.DataFrame({
        "adx": adx,
        "plus_di": plus_di,
        "minus_di": minus_di
    }, index=df.index)

def calculate_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0) -> pd.DataFrame:
    """
    Calculate Supertrend indicator.
    Returns DataFrame with columns 'supertrend', 'direction', 'long_band', 'short_band'.
    """
    try:
        import pandas_ta as ta
        st_df = ta.supertrend(df["high"], df["low"], df["close"], length=period, multiplier=multiplier)
        if st_df is not None:
            return pd.DataFrame({
                "supertrend": st_df.iloc[:, 0],
                "direction": st_df.iloc[:, 1],
                "long_band": st_df.iloc[:, 2],
                "short_band": st_df.iloc[:, 3]
            }, index=df.index)
    except Exception:
        pass

    # Custom implementation
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    # Calculate ATR
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
        # Calculate Final Upper Band
        if basic_ub.iloc[i] < final_ub.iloc[i-1] or close.iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]
            
        # Calculate Final Lower Band
        if basic_lb.iloc[i] > final_lb.iloc[i-1] or close.iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]
            
        # Calculate Supertrend value and direction
        if supertrend.iloc[i-1] == final_ub.iloc[i-1]:
            if close.iloc[i] > final_ub.iloc[i]:
                supertrend.iloc[i] = final_lb.iloc[i]
                direction.iloc[i] = 1 # bullish
            else:
                supertrend.iloc[i] = final_ub.iloc[i]
                direction.iloc[i] = -1 # bearish
        else:
            if close.iloc[i] < final_lb.iloc[i]:
                supertrend.iloc[i] = final_ub.iloc[i]
                direction.iloc[i] = -1 # bearish
            else:
                supertrend.iloc[i] = final_lb.iloc[i]
                direction.iloc[i] = 1 # bullish
                
    return pd.DataFrame({
        "supertrend": supertrend,
        "direction": direction,
        "long_band": final_lb,
        "short_band": final_ub
    }, index=df.index)

def calculate_range_filter(df: pd.DataFrame, period: int = 14, multiplier: float = 1.5) -> pd.DataFrame:
    """
    Calculate Range Filter indicator (similar to TradingView Range Filter Buy/Sell).
    Returns DataFrame with columns 'range_filter', 'range_direction', 'range_buy', 'range_sell'.
    """
    close = df["close"]
    
    # Calculate Range Size: EMA of absolute price changes
    price_change = (close - close.shift(1)).abs()
    # Handle NaN for first row
    price_change.iloc[0] = 0.0
    range_size = price_change.ewm(span=period, adjust=False).mean() * multiplier
    
    filter_val = close.copy()
    
    # Iterate and calculate filter value
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
            
    # Calculate direction and buy/sell signals
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

def add_trend_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all trend indicators to the DataFrame."""
    d = df.copy()
    d["sma_20"] = calculate_sma(d, 20)
    d["sma_50"] = calculate_sma(d, 50)
    d["sma_200"] = calculate_sma(d, 200)
    d["ema_9"] = calculate_ema(d, 9)
    d["ema_21"] = calculate_ema(d, 21)
    
    macd_df = calculate_macd(d)
    d = pd.concat([d, macd_df], axis=1)
    
    adx_df = calculate_adx(d)
    d = pd.concat([d, adx_df], axis=1)
    
    st_df = calculate_supertrend(d)
    d = pd.concat([d, st_df], axis=1)
    
    rf_df = calculate_range_filter(d)
    d = pd.concat([d, rf_df], axis=1)
    return d

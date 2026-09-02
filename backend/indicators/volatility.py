import pandas as pd
import numpy as np

def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0, column: str = "close") -> pd.DataFrame:
    """
    Calculate Bollinger Bands (Upper, Middle, Lower, %B, and Bandwidth).
    """
    middle = df[column].rolling(window=period).mean()
    std = df[column].rolling(window=period).std()
    
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    
    # %B = (Price - Lower Band) / (Upper Band - Lower Band)
    pct_b = (df[column] - lower) / (upper - lower + 1e-10)
    
    # BandWidth = (Upper Band - Lower Band) / Middle Band * 100
    bandwidth = ((upper - lower) / (middle + 1e-10)) * 100.0
    
    return pd.DataFrame({
        "bb_upper": upper,
        "bb_middle": middle,
        "bb_lower": lower,
        "bb_pct_b": pct_b,
        "bb_bandwidth": bandwidth
    }, index=df.index)

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate Average True Range (ATR) and Normalized ATR (% of close)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    natr = (atr / (close + 1e-10)) * 100.0
    
    return pd.DataFrame({
        "atr_14": atr,
        "natr_14": natr
    }, index=df.index)

def calculate_keltner_channels(df: pd.DataFrame, ema_period: int = 20, atr_period: int = 10, multiplier: float = 1.5) -> pd.DataFrame:
    """
    Calculate Keltner Channels (Upper, Middle EMA, Lower).
    """
    close = df["close"]
    middle = close.ewm(span=ema_period, adjust=False).mean()
    
    atr_df = calculate_atr(df, atr_period)
    atr = atr_df["atr_14"]
    
    upper = middle + (multiplier * atr)
    lower = middle - (multiplier * atr)
    
    return pd.DataFrame({
        "kc_upper": upper,
        "kc_middle": middle,
        "kc_lower": lower
    }, index=df.index)

def calculate_donchian_channels(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Calculate Donchian Channels (20-period Highest High, Lowest Low, Middle).
    """
    upper = df["high"].rolling(window=period).max()
    lower = df["low"].rolling(window=period).min()
    middle = (upper + lower) / 2.0
    
    return pd.DataFrame({
        "dc_upper": upper,
        "dc_middle": middle,
        "dc_lower": lower
    }, index=df.index)

def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all volatility indicators to the DataFrame."""
    d = df.copy()
    bb_df = calculate_bollinger_bands(d)
    d = pd.concat([d, bb_df], axis=1)
    
    atr_df = calculate_atr(d)
    d = pd.concat([d, atr_df], axis=1)
    
    kc_df = calculate_keltner_channels(d)
    d = pd.concat([d, kc_df], axis=1)
    
    dc_df = calculate_donchian_channels(d)
    d = pd.concat([d, dc_df], axis=1)
    
    # Bollinger Squeeze detection: BB Upper < KC Upper and BB Lower > KC Lower
    d["bb_squeeze"] = (d["bb_upper"] < d["kc_upper"]) & (d["bb_lower"] > d["kc_lower"])
    return d


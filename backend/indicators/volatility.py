import pandas as pd
import numpy as np

def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0, column: str = "close") -> pd.DataFrame:
    """
    Calculate Bollinger Bands (Upper, Middle, Lower).
    """
    middle = df[column].rolling(window=period).mean()
    std = df[column].rolling(window=period).std()
    
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    
    return pd.DataFrame({
        "bb_upper": upper,
        "bb_middle": middle,
        "bb_lower": lower
    }, index=df.index)

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr

def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all volatility indicators to the DataFrame."""
    d = df.copy()
    bb_df = calculate_bollinger_bands(d)
    d = pd.concat([d, bb_df], axis=1)
    d["atr_14"] = calculate_atr(d)
    return d

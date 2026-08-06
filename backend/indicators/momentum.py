import pandas as pd
import numpy as np

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    close = df["close"]
    delta = close.diff()
    
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Wilder's smoothing
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi

def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    """
    Calculate Stochastic Oscillator (%K and %D).
    """
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    
    k = 100.0 * ((df["close"] - low_min) / (high_max - low_min + 1e-10))
    d = k.rolling(window=d_period).mean()
    
    return pd.DataFrame({
        "stoch_k": k,
        "stoch_d": d
    }, index=df.index)

def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate Commodity Channel Index (CCI)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    tp_sma = tp.rolling(window=period).mean()
    
    # Mean Absolute Deviation
    def mad(x):
        return np.abs(x - x.mean()).mean()
        
    tp_mad = tp.rolling(window=period).apply(mad, raw=True)
    cci = (tp - tp_sma) / (0.015 * tp_mad + 1e-10)
    return cci

def add_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all momentum indicators to the DataFrame."""
    d = df.copy()
    d["rsi_14"] = calculate_rsi(d)
    
    stoch_df = calculate_stochastic(d)
    d = pd.concat([d, stoch_df], axis=1)
    
    d["cci_20"] = calculate_cci(d)
    return d

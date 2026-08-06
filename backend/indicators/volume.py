import pandas as pd
import numpy as np
from typing import Tuple

def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """Calculate On-Balance Volume (OBV)."""
    close = df["close"]
    volume = df["volume"]
    
    prev_close = close.shift(1)
    
    # OBV calculation
    obv_direction = np.zeros(len(df))
    obv_direction[close > prev_close] = 1.0
    obv_direction[close < prev_close] = -1.0
    
    obv = (obv_direction * volume).cumsum()
    return pd.Series(obv, index=df.index)

def calculate_cmf(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate Chaikin Money Flow (CMF)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]
    
    # Money Flow Multiplier
    mf_multiplier = ((close - low) - (high - close)) / (high - low + 1e-10)
    # Money Flow Volume
    mf_volume = mf_multiplier * volume
    
    cmf = mf_volume.rolling(window=period).sum() / (volume.rolling(window=period).sum() + 1e-10)
    return cmf

def calculate_volume_profile(df: pd.DataFrame, bins: int = 30) -> Tuple[float, float, float]:
    """
    Calculate Volume Profile metrics:
    - POC: Point of Control (price level with max volume)
    - VAH: Value Area High (upper boundary of 70% volume)
    - VAL: Value Area Low (lower boundary of 70% volume)
    """
    if df.empty or len(df) < 5:
        return 0.0, 0.0, 0.0
        
    min_p = float(df["low"].min())
    max_p = float(df["high"].max())
    if min_p == max_p:
        return min_p, min_p, min_p
        
    price_bins = np.linspace(min_p, max_p, bins)
    bin_width = price_bins[1] - price_bins[0]
    
    volumes = np.zeros(bins)
    
    # Assign volumes to bins
    for _, row in df.iterrows():
        close_p = row["close"]
        vol = row["volume"]
        
        bin_idx = np.digitize(close_p, price_bins) - 1
        bin_idx = max(0, min(bin_idx, bins - 1))
        volumes[bin_idx] += vol
        
    # Find POC
    poc_idx = int(np.argmax(volumes))
    poc = float(price_bins[poc_idx] + (bin_width / 2))
    
    # Value Area (70% of total volume centered around POC)
    total_vol = volumes.sum()
    if total_vol == 0:
        return poc, poc, poc
        
    target_vol = total_vol * 0.70
    
    va_indices = [poc_idx]
    current_vol = volumes[poc_idx]
    
    left = poc_idx - 1
    right = poc_idx + 1
    
    while current_vol < target_vol and (left >= 0 or right < bins):
        vol_l = volumes[left] if left >= 0 else 0
        vol_r = volumes[right] if right < bins else 0
        
        if vol_l >= vol_r and left >= 0:
            va_indices.append(left)
            current_vol += vol_l
            left -= 1
        elif right < bins:
            va_indices.append(right)
            current_vol += vol_r
            right += 1
        else:
            break
            
    va_prices = [price_bins[i] for i in va_indices]
    vah = float(max(va_prices) + bin_width)
    val = float(min(va_prices))
    
    return poc, vah, val

def add_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add OBV and CMF to the DataFrame."""
    d = df.copy()
    d["obv"] = calculate_obv(d)
    d["cmf_20"] = calculate_cmf(d)
    return d

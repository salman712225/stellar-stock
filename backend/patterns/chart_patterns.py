import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple

def find_pivots(df: pd.DataFrame, window: int = 5) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """
    Find local peaks (highs) and troughs (lows) in the price series.
    Returns: (peaks, troughs) as lists of (index, price) tuples.
    """
    peaks = []
    troughs = []
    
    high = df["high"].values
    low = df["low"].values
    
    for i in range(window, len(df) - window):
        # Peak: high[i] is greater than all highs in window around it
        is_peak = True
        for w in range(1, window + 1):
            if high[i] < high[i - w] or high[i] < high[i + w]:
                is_peak = False
                break
        if is_peak:
            peaks.append((i, float(high[i])))
            
        # Trough: low[i] is lower than all lows in window around it
        is_trough = True
        for w in range(1, window + 1):
            if low[i] > low[i - w] or low[i] > low[i + w]:
                is_trough = False
                break
        if is_trough:
            troughs.append((i, float(low[i])))
            
    return peaks, troughs

def detect_support_resistance(df: pd.DataFrame, window: int = 5, tolerance_pct: float = 1.0) -> List[float]:
    """
    Find major support/resistance levels by clustering nearby pivots.
    """
    peaks, troughs = find_pivots(df, window)
    all_pivots = [p[1] for p in peaks] + [t[1] for t in troughs]
    if not all_pivots:
        return []
        
    levels = []
    # Cluster pivots that are close to each other
    for p in sorted(all_pivots):
        if not levels:
            levels.append(p)
        else:
            # Check if this pivot is close to the last clustered level
            last_level = levels[-1]
            diff_pct = abs(p - last_level) / last_level * 100.0
            if diff_pct <= tolerance_pct:
                # Average them out
                levels[-1] = (last_level + p) / 2.0
            else:
                levels.append(p)
                
    return levels

def detect_double_patterns(df: pd.DataFrame, window: int = 5, tolerance_pct: float = 1.5) -> Dict[str, List[int]]:
    """
    Detect Double Tops and Double Bottoms in the chart.
    Returns: Dict containing indices of detected patterns.
    """
    peaks, troughs = find_pivots(df, window)
    
    double_tops = []
    double_bottoms = []
    
    # Double Top: Two consecutive peaks at roughly same price
    for i in range(len(peaks) - 1):
        idx1, p1 = peaks[i]
        idx2, p2 = peaks[i+1]
        
        # Check tolerance
        diff = abs(p1 - p2) / min(p1, p2) * 100.0
        if diff <= tolerance_pct:
            # Find the trough between these peaks
            mid_troughs = [t[1] for t in troughs if idx1 < t[0] < idx2]
            if mid_troughs:
                trough_val = min(mid_troughs)
                # Ensure current price broke or is testing the neckline
                double_tops.append(idx2)
                
    # Double Bottom: Two consecutive troughs at roughly same price
    for i in range(len(troughs) - 1):
        idx1, t1 = troughs[i]
        idx2, t2 = troughs[i+1]
        
        diff = abs(t1 - t2) / min(t1, t2) * 100.0
        if diff <= tolerance_pct:
            # Find the peak between these troughs
            mid_peaks = [p[1] for p in peaks if idx1 < p[0] < idx2]
            if mid_peaks:
                peak_val = max(mid_peaks)
                double_bottoms.append(idx2)
                
    return {
        "double_tops": double_tops,
        "double_bottoms": double_bottoms
    }

def detect_channels(df: pd.DataFrame, lookback: int = 30) -> Dict[str, Any]:
    """
    Detect if the asset is trading in a channel.
    Uses linear regression on high and low pivot points.
    """
    if len(df) < lookback:
        return {"type": "none", "slope": 0.0}
        
    recent = df.tail(lookback).copy()
    x = np.arange(len(recent))
    
    # Fit regression line to highs
    high_slope, high_intercept = np.polyfit(x, recent["high"].values, 1)
    # Fit regression line to lows
    low_slope, low_intercept = np.polyfit(x, recent["low"].values, 1)
    
    # Average slope
    avg_slope = (high_slope + low_slope) / 2.0
    
    # Check if lines are roughly parallel (slope difference is small compared to average price)
    price_mean = recent["close"].mean()
    slope_diff = abs(high_slope - low_slope) / price_mean * 100.0
    
    if slope_diff < 0.5: # lines are parallel
        if avg_slope > 0.0002 * price_mean:
            channel_type = "ascending"
        elif avg_slope < -0.0002 * price_mean:
            channel_type = "descending"
        else:
            channel_type = "horizontal"
    else:
        channel_type = "none"
        
    return {
        "type": channel_type,
        "slope": avg_slope,
        "upper_intercept": high_intercept,
        "lower_intercept": low_intercept
    }

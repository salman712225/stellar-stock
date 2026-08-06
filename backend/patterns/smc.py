import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from patterns.chart_patterns import find_pivots

def detect_fvgs(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect Fair Value Gaps (FVG) or imbalances.
    Bullish FVG: candle 1 high < candle 3 low
    Bearish FVG: candle 1 low > candle 3 high
    """
    fvgs = []
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    timestamps = df["timestamp"].values
    
    for i in range(2, len(df)):
        # 1. Bullish FVG (Buying Imbalance)
        if highs[i-2] < lows[i]:
            # Verify it's a strong expansion (candle i-1 is large bullish)
            if closes[i-1] > df["open"].values[i-1]:
                fvgs.append({
                    "index": i-1,
                    "timestamp": int(timestamps[i-1]),
                    "type": "bullish_fvg",
                    "top": float(lows[i]),
                    "bottom": float(highs[i-2]),
                    "mitigated": False, # Will check mitigation later
                    "price_range": (float(highs[i-2]), float(lows[i]))
                })
                
        # 2. Bearish FVG (Selling Imbalance)
        elif lows[i-2] > highs[i]:
            # Verify it's a strong expansion (candle i-1 is large bearish)
            if closes[i-1] < df["open"].values[i-1]:
                fvgs.append({
                    "index": i-1,
                    "timestamp": int(timestamps[i-1]),
                    "type": "bearish_fvg",
                    "top": float(lows[i-2]),
                    "bottom": float(highs[i]),
                    "mitigated": False,
                    "price_range": (float(highs[i]), float(lows[i-2]))
                })
                
    # Check mitigation (if price later crossed/filled the gap)
    for fvg in fvgs:
        idx = fvg["index"]
        fvg_type = fvg["type"]
        top = fvg["top"]
        bottom = fvg["bottom"]
        
        # Look at candles after the FVG index
        for j in range(idx + 2, len(df)):
            if fvg_type == "bullish_fvg":
                # Mitigated if price falls below the top of FVG
                if lows[j] <= top:
                    fvg["mitigated"] = True
                    fvg["mitigated_index"] = j
                    break
            else:
                # Mitigated if price rises above the bottom of FVG
                if highs[j] >= bottom:
                    fvg["mitigated"] = True
                    fvg["mitigated_index"] = j
                    break
                    
    return fvgs

def scan_smc_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Scan Smart Money Concepts:
    - Order Blocks (OB)
    - Break of Structure (BoS)
    - Change of Character (CHoCH)
    """
    peaks, troughs = find_pivots(df, window=5)
    
    order_blocks = []
    bos_list = []
    choch_list = []
    
    # Initialize structural variables
    last_high = None
    last_low = None
    trend = "bullish"  # default starting assumption
    
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    opens = df["open"].values
    timestamps = df["timestamp"].values
    
    # Simple loop to track structural breaks
    for i in range(10, len(df)):
        # Update last swing high / low from our pivot lists
        current_peaks = [p for p in peaks if p[0] < i]
        current_troughs = [t for t in troughs if t[0] < i]
        
        if current_peaks:
            last_high = current_peaks[-1][1]
            last_high_idx = current_peaks[-1][0]
        if current_troughs:
            last_low = current_troughs[-1][1]
            last_low_idx = current_troughs[-1][0]
            
        if last_high is None or last_low is None:
            continue
            
        # 1. Break of Structure (BoS) or Change of Character (CHoCH)
        # Price closes above previous swing high
        if closes[i] > last_high:
            if trend == "bullish":
                # Trend continuation = BoS
                bos_list.append({
                    "index": i,
                    "timestamp": int(timestamps[i]),
                    "type": "bullish_bos",
                    "price": last_high
                })
            else:
                # Trend reversal = CHoCH
                trend = "bullish"
                choch_list.append({
                    "index": i,
                    "timestamp": int(timestamps[i]),
                    "type": "bullish_choch",
                    "price": last_high
                })
                
            # Create Bullish Order Block (last bearish candle before the swing high breakout)
            # Find the most recent bearish candle before breakout
            for j in range(i, 0, -1):
                if closes[j] < opens[j]:
                    order_blocks.append({
                        "index": j,
                        "timestamp": int(timestamps[j]),
                        "type": "bullish_ob",
                        "high": float(highs[j]),
                        "low": float(lows[j]),
                        "mitigated": False
                    })
                    break
                    
        # Price closes below previous swing low
        elif closes[i] < last_low:
            if trend == "bearish":
                # Trend continuation = BoS
                bos_list.append({
                    "index": i,
                    "timestamp": int(timestamps[i]),
                    "type": "bearish_bos",
                    "price": last_low
                })
            else:
                # Trend reversal = CHoCH
                trend = "bearish"
                choch_list.append({
                    "index": i,
                    "timestamp": int(timestamps[i]),
                    "type": "bearish_choch",
                    "price": last_low
                })
                
            # Create Bearish Order Block (last bullish candle before the swing low breakout)
            for j in range(i, 0, -1):
                if closes[j] > opens[j]:
                    order_blocks.append({
                        "index": j,
                        "timestamp": int(timestamps[j]),
                        "type": "bearish_ob",
                        "high": float(highs[j]),
                        "low": float(lows[j]),
                        "mitigated": False
                    })
                    break
                    
    # Check mitigation of Order Blocks
    for ob in order_blocks:
        idx = ob["index"]
        ob_type = ob["type"]
        high_val = ob["high"]
        low_val = ob["low"]
        
        for j in range(idx + 1, len(df)):
            if ob_type == "bullish_ob":
                # Bullish OB is mitigated when price hits/goes below its low
                if lows[j] <= low_val:
                    ob["mitigated"] = True
                    ob["mitigated_index"] = j
                    break
            else:
                # Bearish OB is mitigated when price hits/goes above its high
                if highs[j] >= high_val:
                    ob["mitigated"] = True
                    ob["mitigated_index"] = j
                    break
                    
    return {
        "order_blocks": order_blocks,
        "bos": bos_list,
        "choch": choch_list,
        "fvgs": detect_fvgs(df)
    }

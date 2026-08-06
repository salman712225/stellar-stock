import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from patterns.chart_patterns import find_pivots

def scan_elliott_waves(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Scans the recent price pivots to check if they conform to
    a standard 5-wave Elliott Impulse Wave (1-2-3-4-5).
    Rules checked:
    1. Wave 2 must not retrace more than 100% of Wave 1.
    2. Wave 3 is typically the longest, and must NOT be the shortest of Waves 1, 3, and 5.
    3. Wave 4 must not enter the price territory of Wave 1.
    """
    peaks, troughs = find_pivots(df, window=5)
    
    # Combine and sort pivots chronologically
    all_pivots = []
    for idx, price in peaks:
        all_pivots.append({"index": idx, "price": price, "type": "high"})
    for idx, price in troughs:
        all_pivots.append({"index": idx, "price": price, "type": "low"})
        
    all_pivots.sort(key=lambda x: x["index"])
    
    # We need at least 6 pivots to form a 5-wave structure (Start, 1, 2, 3, 4, 5)
    if len(all_pivots) < 6:
        return {"detected": False, "wave_type": "none", "points": []}
        
    recent_pivots = all_pivots[-6:]
    p0 = recent_pivots[0]
    p1 = recent_pivots[1]
    p2 = recent_pivots[2]
    p3 = recent_pivots[3]
    p4 = recent_pivots[4]
    p5 = recent_pivots[5]

    # Check for Bullish Impulse Wave (Low-High-Low-High-Low-High)
    if (p0["type"] == "low" and p1["type"] == "high" and p2["type"] == "low" and
        p3["type"] == "high" and p4["type"] == "low" and p5["type"] == "high"):
        
        # Calculate wave lengths
        wave1 = p1["price"] - p0["price"]
        wave2 = p1["price"] - p2["price"]
        wave3 = p3["price"] - p2["price"]
        wave4 = p3["price"] - p4["price"]
        wave5 = p5["price"] - p4["price"]
        
        # Rule 1: Wave 2 doesn't retrace below start of Wave 1
        r1 = p2["price"] > p0["price"]
        # Rule 2: Wave 3 goes higher than Wave 1 high
        r2 = p3["price"] > p1["price"]
        # Rule 3: Wave 4 doesn't overlap Wave 1 peak
        r3 = p4["price"] > p1["price"]
        # Rule 4: Wave 5 goes higher than Wave 3 peak
        r4 = p5["price"] > p3["price"]
        # Rule 5: Wave 3 is not the shortest of 1, 3, 5
        r5 = not (wave3 < wave1 and wave3 < wave5)

        if r1 and r2 and r3 and r4 and r5:
            return {
                "detected": True,
                "wave_type": "bullish_impulse",
                "points": [p0["index"], p1["index"], p2["index"], p3["index"], p4["index"], p5["index"]],
                "prices": [p0["price"], p1["price"], p2["price"], p3["price"], p4["price"], p5["price"]]
            }

    # Check for Bearish Impulse Wave (High-Low-High-Low-High-Low)
    elif (p0["type"] == "high" and p1["type"] == "low" and p2["type"] == "high" and
          p3["type"] == "low" and p4["type"] == "high" and p5["type"] == "low"):
          
        # Calculate wave lengths (magnitudes)
        wave1 = p0["price"] - p1["price"]
        wave2 = p2["price"] - p1["price"]
        wave3 = p2["price"] - p3["price"]
        wave4 = p4["price"] - p3["price"]
        wave5 = p4["price"] - p5["price"]
        
        r1 = p2["price"] < p0["price"]
        r2 = p3["price"] < p1["price"]
        r3 = p4["price"] < p1["price"]
        r4 = p5["price"] < p3["price"]
        r5 = not (wave3 < wave1 and wave3 < wave5)

        if r1 and r2 and r3 and r4 and r5:
            return {
                "detected": True,
                "wave_type": "bearish_impulse",
                "points": [p0["index"], p1["index"], p2["index"], p3["index"], p4["index"], p5["index"]],
                "prices": [p0["price"], p1["price"], p2["price"], p3["price"], p4["price"], p5["price"]]
            }

    return {"detected": False, "wave_type": "none", "points": []}

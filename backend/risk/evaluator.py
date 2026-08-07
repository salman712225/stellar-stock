import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from data.options_data import calculate_greeks

logger = logging.getLogger("position_evaluator")

def evaluate_position(
    symbol: str,
    position_type: str,  # "long", "short", "call", "put"
    entry_price: float,  # price user bought at (for options, this is the premium they paid)
    limit_price: float,  # exit target (for options, this is the premium target OR underlying target)
    stop_loss: float,    # stop loss price
    spot_price: float,   # current price of underlying
    strike: Optional[float] = None, # option strike price if call/put
    df_enriched: Optional[pd.DataFrame] = None,
    smc_data: Optional[Dict[str, Any]] = None,
    options_chain: Optional[Dict[str, Any]] = None,
    sentiment_score: float = 0.0,
    prediction: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates an open trading position and outputs quantitative suggestion metrics.
    """
    is_option = position_type.lower() in ["call", "put"]
    
    # 1. Option-specific Premium calculations
    current_premium = None
    option_greeks = {}
    
    if is_option and strike and options_chain:
        contracts = options_chain.get("calls" if position_type.lower() == "call" else "puts", [])
        # Find exact contract
        matched_contract = None
        for contract in contracts:
            if abs(contract["strike"] - strike) < 0.01:
                matched_contract = contract
                break
                
        if matched_contract:
            current_premium = matched_contract["lastPrice"]
            option_greeks = {
                "delta": matched_contract["delta"],
                "gamma": matched_contract["gamma"],
                "theta": matched_contract["theta"],
                "vega": matched_contract["vega"],
                "impliedVolatility": matched_contract["impliedVolatility"]
            }
        else:
            # Theoretical fallback using Black-Scholes
            r = 0.05
            expiry_timestamp = options_chain.get("selected_expiry")
            if expiry_timestamp:
                current_time = datetime.now(timezone.utc).timestamp()
                T = max(1e-5, (expiry_timestamp - current_time) / (365 * 24 * 3600))
            else:
                T = 7 / 365.0 # assume 7 days to expiry default
                
            iv = 0.25 # default 25% IV
            greeks = calculate_greeks(position_type.lower(), spot_price, strike, T, r, iv)
            current_premium = greeks["price"]
            option_greeks = {
                "delta": greeks["delta"],
                "gamma": greeks["gamma"],
                "theta": greeks["theta"],
                "vega": greeks["vega"],
                "impliedVolatility": iv
            }

    # 2. PnL calculations
    if is_option:
        # PnL based on premium change
        comp_price = current_premium if current_premium is not None else entry_price
        pnl_pct = ((comp_price - entry_price) / entry_price) * 100.0 if entry_price > 0 else 0.0
    else:
        # Futures/Spot PnL based on underlying price change
        if position_type.lower() == "long":
            pnl_pct = ((spot_price - entry_price) / entry_price) * 100.0 if entry_price > 0 else 0.0
        else: # short
            pnl_pct = ((entry_price - spot_price) / entry_price) * 100.0 if entry_price > 0 else 0.0

    # 3. Obstacle Scanner (Roadblocks between current price and limit target)
    roadblocks = []
    
    # We check if there are unmitigated Order Blocks or Key S&R levels in the way
    if df_enriched is not None and not df_enriched.empty:
        # Get support/resistance levels
        from patterns.chart_patterns import detect_support_resistance
        levels = detect_support_resistance(df_enriched, window=5)
        
        # Check Order Blocks
        obs = smc_data.get("order_blocks", []) if smc_data else []
        unmit_obs = [ob for ob in obs if not ob.get("mitigated")]
        
        if position_type.lower() in ["long", "call"]:
            # Obstacles are resistance levels/order blocks higher than spot but below limit target
            target_boundary = limit_price if not is_option else strike + limit_price
            
            # S&R resistance check
            resistances = [l for l in levels if spot_price < l < target_boundary]
            for r in resistances:
                roadblocks.append({
                    "type": "resistance_level",
                    "price": round(r, 2),
                    "description": f"Historical resistance level at ${r:.2f}"
                })
                
            # Bearish Order Blocks check
            bearish_obs = [ob for ob in unmit_obs if ob["type"] == "bearish_ob" and spot_price < ob["high"] < target_boundary]
            for ob in bearish_obs:
                roadblocks.append({
                    "type": "order_block_resistance",
                    "price": round(ob["high"], 2),
                    "description": f"Bearish Order Block (institutional selling supply) at ${ob['high']:.2f}"
                })
        else:
            # Obstacles are support levels/order blocks lower than spot but above limit target
            target_boundary = limit_price if not is_option else max(0.1, strike - limit_price)
            
            supports = [l for l in levels if target_boundary < l < spot_price]
            for s in supports:
                roadblocks.append({
                    "type": "support_level",
                    "price": round(s, 2),
                    "description": f"Historical support level at ${s:.2f}"
                })
                
            # Bullish Order Blocks check
            bullish_obs = [ob for ob in unmit_obs if ob["type"] == "bullish_ob" and target_boundary < ob["low"] < spot_price]
            for ob in bullish_obs:
                roadblocks.append({
                    "type": "order_block_support",
                    "price": round(ob["low"], 2),
                    "description": f"Bullish Order Block (institutional buying demand) at ${ob['low']:.2f}"
                })

    # 4. ML Forecast alignment check
    ml_sig = prediction.get("signal", "HOLD") if prediction else "HOLD"
    ml_conf = prediction.get("confidence", 0.5) if prediction else 0.5
    
    ml_aligned = False
    if position_type.lower() in ["long", "call"] and ml_sig == "BUY":
        ml_aligned = True
    elif position_type.lower() in ["short", "put"] and ml_sig == "SELL":
        ml_aligned = True

    # 5. Priority-Based Rule Engine
    action = "HOLD"
    rationale_list = []
    
    # Priority 1 & 2: Stop Loss & Limit Exit Check
    is_stop_loss_breached = False
    if position_type.lower() in ["long", "call"]:
        if spot_price <= stop_loss:
            is_stop_loss_breached = True
    else:
        if spot_price >= stop_loss:
            is_stop_loss_breached = True
            
    is_limit_reached = False
    if position_type.lower() in ["long", "call"]:
        if spot_price >= limit_price:
            is_limit_reached = True
    else:
        if spot_price <= limit_price:
            is_limit_reached = True

    if is_stop_loss_breached:
        action = "EXIT NOW"
        rationale_list.append(f"CRITICAL RISK: Stop loss level of ${stop_loss:,.2f} breached (Spot: ${spot_price:,.2f}).")
    elif is_limit_reached:
        action = "TAKE PROFIT"
        rationale_list.append(f"TARGET ACHIEVED: Profit exit target of ${limit_price:,.2f} reached (Spot: ${spot_price:,.2f}).")
    else:
        # Priority 3: ML Forecast Trend Reversal
        if ml_sig != "HOLD" and not ml_aligned and ml_conf > 0.58:
            action = "EXIT NOW" if pnl_pct > -3 else "HOLD"
            rationale_list.append(f"ML REVERSAL: High-confidence ({ml_conf*100:.0f}%) ML signal flipped to {ml_sig}. Direction conflict detected.")
        
        # Priority 4: Option Theta Decay
        elif is_option and option_greeks:
            theta = option_greeks.get("theta", 0.0)
            if abs(theta) > 0.02 * entry_price and not ml_aligned:
                action = "EXIT NOW"
                rationale_list.append(f"THETA DECAY: Time decay rate ({abs(theta):.4f}/day) is eroding option premium while underlying is consolidating.")
                
        # Priority 5: Technical Roadblocks
        elif len(roadblocks) >= 2:
            action = "EXIT NOW" if pnl_pct > 0 else "TAKE PROFIT (REDUCED TARGET)"
            block_type = "resistance" if position_type.lower() in ["long", "call"] else "support"
            rationale_list.append(f"ROADBLOCKS AHEAD: {len(roadblocks)} institutional {block_type} areas block target path. Suggest securing PnL.")

        # Priority 6: Average Down Opportunity
        elif position_type.lower() in ["long", "call"] and pnl_pct < -5.0:
            near_support = False
            if smc_data:
                for ob in smc_data.get("order_blocks", []):
                    if ob["type"] == "bullish_ob" and not ob.get("mitigated"):
                        if ob["low"] <= spot_price <= ob["high"]:
                            near_support = True
                            break
            if near_support and ml_sig == "BUY":
                action = "AVERAGE DOWN"
                rationale_list.append("AVERAGE DOWN: Price testing an unmitigated bullish Order Block with supportive bullish ML forecast.")

    # Priority 7: Trend continuity (general hold)
    if not rationale_list:
        action = "HOLD"
        rationale_list.append("TREND ALIGNED: Trend structure is healthy. No key institutional roadblocks detected between spot and target.")

    # Target progress %
    total_range = abs(limit_price - entry_price)
    current_dist = abs(spot_price - entry_price)
    progress_pct = min(100.0, max(0.0, (current_dist / total_range) * 100.0)) if total_range > 0 else 0.0
    if pnl_pct < 0:
        progress_pct = 0.0

    # Calculate simple advice (Keep it / Sell it)
    if action in ["EXIT NOW", "TAKE PROFIT", "TAKE PROFIT (REDUCED TARGET)"]:
        simple_advice = "Sell it"
    elif prediction and prediction.get("signal") == "SELL" and prediction.get("confidence", 0.5) > 0.55:
        simple_advice = "Sell it"
    else:
        simple_advice = "Keep it"

    return {
        "symbol": symbol,
        "position_type": position_type,
        "pnl_percentage": round(pnl_pct, 2),
        "current_premium": round(current_premium, 4) if current_premium is not None else None,
        "option_greeks": option_greeks,
        "roadblocks": roadblocks,
        "ml_aligned": ml_aligned,
        "action": action,
        "rationale": " ".join(rationale_list),
        "target_progress_pct": round(progress_pct, 1),
        "spot_price": spot_price,
        "simple_advice": simple_advice
    }

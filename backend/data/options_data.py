import httpx
import math
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger("options_data")

# Normal Distribution functions using Python's standard math library
def norm_cdf(x: float) -> float:
    """Cumulative distribution function of standard normal distribution."""
    try:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    except (ValueError, OverflowError):
        return 0.0 if x < 0 else 1.0

def norm_pdf(x: float) -> float:
    """Probability density function of standard normal distribution."""
    try:
        return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x**2)
    except (ValueError, OverflowError):
        return 0.0

def calculate_greeks(
    option_type: str,
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float
) -> Dict[str, float]:
    """
    Calculate Black-Scholes option price and Greeks: Delta, Gamma, Theta, Vega.
    S: Underlying price
    K: Strike price
    T: Time to expiration in years (e.g. 7 days = 7/365)
    r: Risk-free rate (e.g. 0.05)
    sigma: Implied Volatility (e.g. 0.20)
    """
    # Safeguards
    if T <= 0:
        T = 1e-5  # avoid division by zero
    if sigma <= 0:
        sigma = 1e-4
    if S <= 0 or K <= 0:
        return {"price": 0.0, "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * norm_pdf(d1) * math.sqrt(T) / 100.0  # Vega per 1% change in IV

        if option_type.lower() == "call":
            price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
            delta = norm_cdf(d1)
            # Theta per calendar day
            theta = (- (S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365.0
        else:
            price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
            delta = norm_cdf(d1) - 1.0
            # Theta per calendar day
            theta = (- (S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365.0

        return {
            "price": max(0.0, price),
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega
        }
    except Exception as e:
        logger.error(f"Error calculating Greeks: {e}")
        return {"price": 0.0, "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

class OptionsDataProvider:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def fetch_options_chain(self, symbol: str, expiry_timestamp: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch options chain for a symbol from Yahoo Finance API.
        If expiry_timestamp is not specified, it fetches the nearest expiry.
        """
        # Symbol parsing for Yahoo
        clean_symbol = symbol
        url = f"https://query2.finance.yahoo.com/v7/finance/options/{clean_symbol}"
        if expiry_timestamp:
            url += f"?date={expiry_timestamp}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=10.0)
                if response.status_code != 200:
                    logger.error(f"Failed to fetch options for {symbol}, status: {response.status_code}")
                    return {}

                res_data = response.json()
                results = res_data.get("optionChain", {}).get("result", [])
                if not results:
                    return {}

                result = results[0]
                expirations = result.get("expirationDates", [])
                underlying_price = result.get("quote", {}).get("regularMarketPrice", 0.0)
                
                options_list = result.get("options", [])
                if not options_list:
                    return {
                        "underlying_price": underlying_price,
                        "expirations": expirations,
                        "calls": [],
                        "puts": []
                    }

                opt = options_list[0]
                calls = opt.get("calls", [])
                puts = opt.get("puts", [])
                selected_expiry = opt.get("expirationDate")

                processed_calls = self._process_options(calls, underlying_price, selected_expiry, "call")
                processed_puts = self._process_options(puts, underlying_price, selected_expiry, "put")

                # Metrics
                pcr_volume, pcr_oi = self.calculate_pcr(processed_calls, processed_puts)
                max_pain = self.calculate_max_pain(processed_calls, processed_puts)

                return {
                    "symbol": symbol,
                    "underlying_price": underlying_price,
                    "expirations": expirations,
                    "selected_expiry": selected_expiry,
                    "selected_expiry_str": datetime.fromtimestamp(selected_expiry, timezone.utc).strftime('%Y-%m-%d') if selected_expiry else "",
                    "calls": processed_calls,
                    "puts": processed_puts,
                    "pcr_volume": pcr_volume,
                    "pcr_oi": pcr_oi,
                    "max_pain": max_pain
                }
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {e}")
            return {}

    def _process_options(self, options_list: List[Dict[str, Any]], S: float, expiry_timestamp: int, option_type: str) -> List[Dict[str, Any]]:
        processed = []
        r = 0.05  # Assume 5% risk free rate
        
        # Calculate time to expiry in years
        current_time = datetime.now(timezone.utc).timestamp()
        time_diff = expiry_timestamp - current_time
        T = max(1e-5, time_diff / (365 * 24 * 3600))

        for opt in options_list:
            strike = float(opt.get("strike", 0.0))
            iv = float(opt.get("impliedVolatility", 0.0))
            
            # Run Greeks calculation
            greeks = calculate_greeks(option_type, S, strike, T, r, iv)
            
            processed.append({
                "contractSymbol": opt.get("contractSymbol", ""),
                "strike": strike,
                "lastPrice": float(opt.get("lastPrice", 0.0)),
                "bid": float(opt.get("bid", 0.0)),
                "ask": float(opt.get("ask", 0.0)),
                "change": float(opt.get("change", 0.0)),
                "percentChange": float(opt.get("percentChange", 0.0)),
                "volume": int(opt.get("volume", 0)) if opt.get("volume") is not None else 0,
                "openInterest": int(opt.get("openInterest", 0)) if opt.get("openInterest") is not None else 0,
                "impliedVolatility": iv,
                "inTheMoney": bool(opt.get("inTheMoney", False)),
                # Calculated Greeks
                "delta": greeks["delta"],
                "gamma": greeks["gamma"],
                "theta": greeks["theta"],
                "vega": greeks["vega"]
            })
        return processed

    def calculate_pcr(self, calls: List[Dict[str, Any]], puts: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Calculate Put-Call Ratio for Volume and Open Interest."""
        total_call_vol = sum(c["volume"] for c in calls)
        total_put_vol = sum(p["volume"] for p in puts)
        
        total_call_oi = sum(c["openInterest"] for c in calls)
        total_put_oi = sum(p["openInterest"] for p in puts)

        pcr_vol = total_put_vol / total_call_vol if total_call_vol > 0 else 0.0
        pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else 0.0

        return round(pcr_vol, 3), round(pcr_oi, 3)

    def calculate_max_pain(self, calls: List[Dict[str, Any]], puts: List[Dict[str, Any]]) -> float:
        """Calculate option pain strike (Max Pain)."""
        all_options = calls + puts
        if not all_options:
            return 0.0
        
        # Unique strike prices
        strikes = sorted(list(set(opt["strike"] for opt in all_options)))
        if not strikes:
            return 0.0

        min_pain = float("inf")
        max_pain_strike = strikes[0]

        for test_strike in strikes:
            total_loss = 0.0
            
            # Calculate call losses if market expires at test_strike
            for c in calls:
                strike = c["strike"]
                oi = c["openInterest"]
                if test_strike > strike:
                    total_loss += (test_strike - strike) * oi
            
            # Calculate put losses if market expires at test_strike
            for p in puts:
                strike = p["strike"]
                oi = p["openInterest"]
                if test_strike < strike:
                    total_loss += (strike - test_strike) * oi
                    
            if total_loss < min_pain:
                min_pain = total_loss
                max_pain_strike = test_strike

        return max_pain_strike

# Singleton instance
options_data_provider = OptionsDataProvider()

import ccxt
import httpx
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
from config import DEFAULT_TIMEFRAME

logger = logging.getLogger("market_data")

class MarketDataProvider:
    def __init__(self):
        # Initialize CCXT exchange client (Binance by default)
        try:
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}  # Use Futures OHLCV for trading analyser
            })
        except Exception as e:
            logger.error(f"Failed to initialize CCXT: {e}. Falling back to Spot/mock.")
            self.exchange = ccxt.binance({'enableRateLimit': True})

    async def fetch_crypto_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        """
        Fetch crypto OHLCV from exchange using CCXT.
        """
        try:
            # CCXT expects fetch_ohlcv to run synchronously or asynchronously depending on exchange.
            # ccxt.binance is synchronous by default unless we use ccxt.pro.
            # We can run it in a thread executor or just call it since it is fast.
            # Let's run it safely.
            loop = httpx.Client() # using a loop-safe sync client or standard run in executor
            
            # Use CCXT sync call
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                return pd.DataFrame()
            
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching crypto data for {symbol}: {e}")
            return pd.DataFrame()

    async def fetch_fo_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        """
        Fetch index/stock OHLCV from Yahoo Finance API.
        """
        # Map timeframe to Yahoo Finance interval
        tf_map = {
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
            "4h": "1h", # Yahoo Finance doesn't have 4h, we use 1h and can aggregate or just use 1h
            "1d": "1d"
        }
        interval = tf_map.get(timeframe, "1h")
        
        # Map limit to Yahoo Finance range
        # Note: 1m data only available for last 7 days, 5m/15m for 60 days, 1h for 730 days.
        range_str = "1mo"
        if interval in ["5m", "15m"]:
            range_str = "60d"
        elif interval == "1h":
            range_str = "730d"
        elif interval == "1d":
            range_str = "5y"

        # Special symbol cleaning for Yahoo Finance
        # Indian assets need .NS (Nifty/Banknifty index: ^NSEI, ^NSEBANK)
        # S&P 500: ^SPX, Apple: AAPL, etc.
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_str}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code != 200:
                    logger.error(f"Yahoo Finance returned status {response.status_code} for {symbol}")
                    return pd.DataFrame()
                
                data = response.json()
                chart_data = data.get("chart", {}).get("result", [])
                if not chart_data:
                    return pd.DataFrame()
                
                result = chart_data[0]
                timestamps = result.get("timestamp", [])
                indicators = result.get("indicators", {}).get("quote", [{}])[0]
                
                opens = indicators.get("open", [])
                highs = indicators.get("high", [])
                lows = indicators.get("low", [])
                closes = indicators.get("close", [])
                volumes = indicators.get("volume", [])
                
                # Align lists
                ohlcv_list = []
                for i in range(len(timestamps)):
                    # Check for None values which Yahoo Finance sometimes returns
                    if (opens[i] is None or highs[i] is None or 
                        lows[i] is None or closes[i] is None):
                        continue
                    ohlcv_list.append([
                        timestamps[i] * 1000, # convert to ms
                        float(opens[i]),
                        float(highs[i]),
                        float(lows[i]),
                        float(closes[i]),
                        float(volumes[i]) if volumes[i] is not None else 0.0
                    ])
                
                df = pd.DataFrame(ohlcv_list, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                
                # Aggregate to 4h if requested (Yahoo Finance doesn't support 4h directly)
                if timeframe == "4h" and not df.empty:
                    df.set_index("datetime", inplace=True)
                    # Resample to 4-hour bars
                    resampled = df.resample("4H").agg({
                        "timestamp": "first",
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum"
                    }).dropna()
                    resampled.reset_index(inplace=True)
                    df = resampled
                
                # Limit size
                return df.tail(limit)
        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance data for {symbol}: {e}")
            return pd.DataFrame()

    async def get_data(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        """
        Generic fetch method that automatically identifies if it's Crypto or F&O/Stock.
        """
        is_crypto = "/" in symbol or symbol.endswith("USDT") or symbol.endswith("USD")
        if is_crypto:
            return await self.fetch_crypto_ohlcv(symbol, timeframe, limit)
        else:
            return await self.fetch_fo_ohlcv(symbol, timeframe, limit)

# Singleton instance
market_data_provider = MarketDataProvider()

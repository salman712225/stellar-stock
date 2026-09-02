import ccxt
import httpx
import pandas as pd
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
from config import DEFAULT_TIMEFRAME, SUPPORTED_TIMEFRAMES

logger = logging.getLogger("market_data")

class MarketDataProvider:
    def __init__(self):
        # Initialize primary CCXT exchange client (Binance)
        try:
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}  # Spot supports broader pairs
            })
        except Exception as e:
            logger.error(f"Failed to initialize CCXT Binance: {e}.")
            self.exchange = None

        # Secondary exchange client for pairs like XAUT (OKX or Gate or Kucoin)
        try:
            self.secondary_exchange = ccxt.okx({
                'enableRateLimit': True
            })
        except Exception:
            self.secondary_exchange = None

    async def fetch_crypto_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        """
        Fetch crypto OHLCV from exchange using CCXT with multi-exchange fallback.
        """
        # Normalize symbol for CCXT
        clean_sym = symbol.replace("-", "/").upper()
        if not "/" in clean_sym and (clean_sym.endswith("USDT") or clean_sym.endswith("USD")):
            if clean_sym.endswith("USDT"):
                clean_sym = f"{clean_sym[:-4]}/USDT"
            elif clean_sym.endswith("USD"):
                clean_sym = f"{clean_sym[:-3]}/USD"

        # 1. Try Primary Exchange (Binance)
        if self.exchange:
            try:
                ohlcv = await asyncio.to_thread(self.exchange.fetch_ohlcv, clean_sym, timeframe, limit=limit)
                if ohlcv and len(ohlcv) > 0:
                    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                    return df
            except Exception as e:
                logger.warning(f"Binance fetch failed for {clean_sym}: {e}. Trying fallback.")

        # 2. Try Secondary Exchange (OKX / KuCoin for XAUT)
        if self.secondary_exchange:
            try:
                ohlcv = await asyncio.to_thread(self.secondary_exchange.fetch_ohlcv, clean_sym, timeframe, limit=limit)
                if ohlcv and len(ohlcv) > 0:
                    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                    return df
            except Exception as e:
                logger.warning(f"Secondary exchange fetch failed for {clean_sym}: {e}.")

        # 3. If symbol is XAUT or Gold Token, try Yahoo Finance XAUT-USD or PAXG-USD
        if "XAUT" in clean_sym or "GOLD" in clean_sym:
            df = await self.fetch_fo_ohlcv("XAUT-USD", timeframe, limit)
            if not df.empty:
                return df
            df = await self.fetch_fo_ohlcv("PAXG-USD", timeframe, limit)
            if not df.empty:
                return df

        # 4. Fallback to Yahoo Finance crypto format (e.g. BTC-USD, ETH-USD, XAUT-USD)
        yahoo_sym = clean_sym.replace("/USDT", "-USD").replace("/USD", "-USD")
        if "/" in yahoo_sym:
            yahoo_sym = yahoo_sym.replace("/", "-")
        df = await self.fetch_fo_ohlcv(yahoo_sym, timeframe, limit)
        if not df.empty:
            return df

        return pd.DataFrame()

    async def fetch_fo_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        """
        Fetch index/stock OHLCV from Yahoo Finance API.
        """
        tf_map = {
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
            "4h": "1h",
            "1d": "1d"
        }
        interval = tf_map.get(timeframe, "1h")
        
        range_str = "1mo"
        if interval in ["5m", "15m"]:
            range_str = "60d"
        elif interval == "1h":
            range_str = "730d"
        elif interval == "1d":
            range_str = "5y"

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_str}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
                
                ohlcv_list = []
                for i in range(len(timestamps)):
                    if (i >= len(opens) or opens[i] is None or 
                        i >= len(highs) or highs[i] is None or 
                        i >= len(lows) or lows[i] is None or 
                        i >= len(closes) or closes[i] is None):
                        continue
                    ohlcv_list.append([
                        timestamps[i] * 1000,
                        float(opens[i]),
                        float(highs[i]),
                        float(lows[i]),
                        float(closes[i]),
                        float(volumes[i]) if (i < len(volumes) and volumes[i] is not None) else 0.0
                    ])
                
                df = pd.DataFrame(ohlcv_list, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                
                if timeframe == "4h" and not df.empty:
                    df.set_index("datetime", inplace=True)
                    resampled = df.resample("4h").agg({
                        "timestamp": "first",
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum"
                    }).dropna()
                    resampled.reset_index(inplace=True)
                    df = resampled
                
                return df.tail(limit)
        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance data for {symbol}: {e}")
            return pd.DataFrame()

    async def get_data(self, symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        """
        Generic fetch method that automatically identifies if it's Crypto or F&O/Stock.
        """
        is_crypto = "/" in symbol or symbol.endswith("USDT") or symbol.endswith("USD") or symbol in ["BTC", "ETH", "XAUT", "SOL", "XRP", "BNB"]
        if is_crypto:
            return await self.fetch_crypto_ohlcv(symbol, timeframe, limit)
        else:
            return await self.fetch_fo_ohlcv(symbol, timeframe, limit)

    async def fetch_multi_timeframe(self, symbol: str, timeframes: List[str] = None, limit: int = 100) -> Dict[str, pd.DataFrame]:
        """
        Fetch data across multiple timeframes concurrently.
        """
        if timeframes is None:
            timeframes = ["5m", "15m", "1h", "4h", "1d"]
            
        tasks = [self.get_data(symbol, tf, limit) for tf in timeframes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        tf_data = {}
        for tf, res in zip(timeframes, results):
            if isinstance(res, pd.DataFrame) and not res.empty:
                tf_data[tf] = res
        return tf_data

    async def get_market_overview(self, symbols: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get real-time snapshot overview for marquee ticker bar.
        """
        if symbols is None:
            symbols = ["BTC/USDT", "ETH/USDT", "XAUT/USDT", "SOL/USDT", "XRP/USDT"]

        results = []
        for sym in symbols:
            try:
                df = await self.get_data(sym, timeframe="1h", limit=25)
                if not df.empty and len(df) >= 2:
                    current = float(df["close"].iloc[-1])
                    prev_24h = float(df["close"].iloc[0])
                    change_pct = ((current - prev_24h) / prev_24h) * 100.0 if prev_24h > 0 else 0.0
                    high_24h = float(df["high"].max())
                    low_24h = float(df["low"].min())
                    vol_24h = float(df["volume"].sum())
                    
                    results.append({
                        "symbol": sym,
                        "price": current,
                        "change_pct": round(change_pct, 2),
                        "high": high_24h,
                        "low": low_24h,
                        "volume": vol_24h
                    })
            except Exception as e:
                logger.warning(f"Failed to get snapshot for {sym}: {e}")
        return results

# Singleton instance
market_data_provider = MarketDataProvider()

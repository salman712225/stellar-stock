import asyncio
import json
import logging
from typing import Dict, Set, Callable, Any
import httpx
import ccxt.async_support as ccxt_async
from config import DEFAULT_CRYPTO_SYMBOLS, DEFAULT_FO_SYMBOLS

logger = logging.getLogger("websocket_feed")

class RealtimeMarketDataFeed:
    def __init__(self):
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self.exchange = None

    async def start(self):
        self.is_running = True
        try:
            self.exchange = ccxt_async.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
        except Exception as e:
            logger.error(f"Failed to initialize async CCXT: {e}")
            self.exchange = None

    async def stop(self):
        self.is_running = False
        for symbol, task in list(self.active_tasks.items()):
            task.cancel()
        if self.exchange:
            await self.exchange.close()
        logger.info("Real-time feed stopped.")

    async def subscribe(self, symbol: str, queue: asyncio.Queue):
        if symbol not in self.subscribers:
            self.subscribers[symbol] = set()
        self.subscribers[symbol].add(queue)
        
        # Start a polling loop task for this symbol if not already active
        if symbol not in self.active_tasks:
            self.active_tasks[symbol] = asyncio.create_task(self._poll_symbol_loop(symbol))
            logger.info(f"Started real-time streaming task for {symbol}")

    async def unsubscribe(self, symbol: str, queue: asyncio.Queue):
        if symbol in self.subscribers:
            self.subscribers[symbol].discard(queue)
            if not self.subscribers[symbol]:
                del self.subscribers[symbol]
                if symbol in self.active_tasks:
                    self.active_tasks[symbol].cancel()
                    del self.active_tasks[symbol]
                    logger.info(f"Stopped streaming task for {symbol} (no subscribers left)")

    async def _poll_symbol_loop(self, symbol: str):
        is_crypto = "/" in symbol or symbol.endswith("USDT") or symbol.endswith("USD")
        
        async_client = httpx.AsyncClient(headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        try:
            while self.is_running:
                price_data = None
                try:
                    if is_crypto:
                        if self.exchange:
                            ticker = await self.exchange.fetch_ticker(symbol)
                            price_data = {
                                "symbol": symbol,
                                "price": ticker.get("last"),
                                "bid": ticker.get("bid"),
                                "ask": ticker.get("ask"),
                                "change_24h": ticker.get("percentage"),
                                "volume_24h": ticker.get("baseVolume"),
                                "timestamp": ticker.get("timestamp")
                            }
                    else:
                        # Fetch quote details from Yahoo Finance
                        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
                        response = await async_client.get(url, timeout=5.0)
                        if response.status_code == 200:
                            res = response.json()
                            quotes = res.get("quoteResponse", {}).get("result", [])
                            if quotes:
                                quote = quotes[0]
                                price_data = {
                                    "symbol": symbol,
                                    "price": quote.get("regularMarketPrice"),
                                    "bid": quote.get("bid", quote.get("regularMarketPrice")),
                                    "ask": quote.get("ask", quote.get("regularMarketPrice")),
                                    "change_24h": quote.get("regularMarketChangePercent"),
                                    "volume_24h": quote.get("regularMarketVolume"),
                                    "timestamp": quote.get("regularMarketTime", 0) * 1000
                                }
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error fetching real-time price for {symbol}: {e}")
                
                if price_data and price_data["price"] is not None:
                    # Broadcast to all registered queues for this symbol
                    queues = list(self.subscribers.get(symbol, []))
                    for q in queues:
                        try:
                            q.put_nowait(price_data)
                        except asyncio.QueueFull:
                            # Pop old item and insert new
                            try:
                                q.get_nowait()
                                q.put_nowait(price_data)
                            except Exception:
                                pass
                
                # Sleep interval: 2 seconds for crypto, 4 seconds for stock/f&o indexes
                await asyncio.sleep(2.0 if is_crypto else 4.0)
        finally:
            await async_client.aclose()

# Singleton instance
live_feed = RealtimeMarketDataFeed()

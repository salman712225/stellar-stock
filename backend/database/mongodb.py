import json
import logging
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import asyncio
from config import MONGO_URI, DB_NAME, DATA_CACHE_DIR

logger = logging.getLogger("db")

class Database:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.use_fallback = True

    async def connect(self):
        try:
            # Short timeout to fail-fast if MongoDB isn't running
            self.client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            # Try to fetch server info to verify connection
            await self.client.server_info()
            self.db = self.client[DB_NAME]
            self.use_fallback = False
            logger.info("Connected to MongoDB successfully.")
            print("Connected to MongoDB successfully.")
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
            logger.warning(f"Could not connect to MongoDB: {e}. Falling back to file-based cache.")
            print(f"MongoDB not available: {e}. Falling back to local file storage.")
            self.use_fallback = True

    def _get_fallback_path(self, collection_name: str) -> str:
        return DATA_CACHE_DIR / f"{collection_name}.json"

    def _read_fallback(self, collection_name: str) -> List[Dict[str, Any]]:
        path = self._get_fallback_path(collection_name)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading fallback file {collection_name}: {e}")
            return []

    def _write_fallback(self, collection_name: str, data: List[Dict[str, Any]]):
        path = self._get_fallback_path(collection_name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Error writing fallback file {collection_name}: {e}")

    # Candlestick (OHLCV) operations
    async def save_ohlcv(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]]):
        if not candles:
            return
        
        # Standardize symbol for DB/File use
        clean_symbol = symbol.replace("/", "_").replace("^", "IDX_")
        
        if not self.use_fallback and self.db is not None:
            collection = self.db[f"ohlcv_{clean_symbol}_{timeframe}"]
            # Upsert candles by timestamp
            for candle in candles:
                await collection.update_one(
                    {"timestamp": candle["timestamp"]},
                    {"$set": candle},
                    upsert=True
                )
        else:
            col_name = f"ohlcv_{clean_symbol}_{timeframe}"
            existing = {c["timestamp"]: c for c in self._read_fallback(col_name)}
            for candle in candles:
                existing[candle["timestamp"]] = candle
            self._write_fallback(col_name, list(existing.values()))

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> List[Dict[str, Any]]:
        clean_symbol = symbol.replace("/", "_").replace("^", "IDX_")
        
        if not self.use_fallback and self.db is not None:
            collection = self.db[f"ohlcv_{clean_symbol}_{timeframe}"]
            cursor = collection.find().sort("timestamp", -1).limit(limit)
            result = await cursor.to_list(length=limit)
            # Return in chronological order
            return sorted(result, key=lambda x: x["timestamp"])
        else:
            col_name = f"ohlcv_{clean_symbol}_{timeframe}"
            data = self._read_fallback(col_name)
            sorted_data = sorted(data, key=lambda x: x.get("timestamp", 0))
            return sorted_data[-limit:]

    # Options Chain caching
    async def save_options_chain(self, symbol: str, expiry: str, chain_data: Dict[str, Any]):
        clean_symbol = symbol.replace("^", "IDX_")
        record = {
            "symbol": symbol,
            "expiry": expiry,
            "timestamp": chain_data.get("timestamp"),
            "data": chain_data
        }
        
        if not self.use_fallback and self.db is not None:
            collection = self.db["options_chains"]
            await collection.update_one(
                {"symbol": symbol, "expiry": expiry},
                {"$set": record},
                upsert=True
            )
        else:
            data = self._read_fallback("options_chains")
            # Remove previous record for same symbol & expiry
            data = [r for r in data if not (r.get("symbol") == symbol and r.get("expiry") == expiry)]
            data.append(record)
            self._write_fallback("options_chains", data)

    async def get_options_chain(self, symbol: str, expiry: str) -> Optional[Dict[str, Any]]:
        if not self.use_fallback and self.db is not None:
            collection = self.db["options_chains"]
            record = await collection.find_one({"symbol": symbol, "expiry": expiry})
            return record["data"] if record else None
        else:
            data = self._read_fallback("options_chains")
            for r in data:
                if r.get("symbol") == symbol and r.get("expiry") == expiry:
                    return r.get("data")
            return None

    # News & Sentiment cache
    async def save_news(self, articles: List[Dict[str, Any]]):
        if not articles:
            return
        if not self.use_fallback and self.db is not None:
            collection = self.db["news"]
            for art in articles:
                # Use url or title as unique identifier
                await collection.update_one(
                    {"url": art.get("url", art.get("title"))},
                    {"$set": art},
                    upsert=True
                )
        else:
            existing = {art.get("url", art.get("title")): art for art in self._read_fallback("news")}
            for art in articles:
                existing[art.get("url", art.get("title"))] = art
            self._write_fallback("news", list(existing.values()))

    async def get_news(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.use_fallback and self.db is not None:
            collection = self.db["news"]
            cursor = collection.find().sort("publishedAt", -1).limit(limit)
            return await cursor.to_list(length=limit)
        else:
            data = self._read_fallback("news")
            # Sort by publishedAt, fallback to index
            data.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)
            return data[:limit]

    # Predictions caching
    async def save_prediction(self, symbol: str, prediction: Dict[str, Any]):
        prediction["symbol"] = symbol
        if not self.use_fallback and self.db is not None:
            collection = self.db["predictions"]
            await collection.update_one(
                {"symbol": symbol},
                {"$set": prediction},
                upsert=True
            )
        else:
            data = self._read_fallback("predictions")
            data = [r for r in data if r.get("symbol") != symbol]
            data.append(prediction)
            self._write_fallback("predictions", data)

    async def get_prediction(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not self.use_fallback and self.db is not None:
            collection = self.db["predictions"]
            return await collection.find_one({"symbol": symbol})
        else:
            data = self._read_fallback("predictions")
            for r in data:
                if r.get("symbol") == symbol:
                    return r
            return None

# Singleton instance
db = Database()

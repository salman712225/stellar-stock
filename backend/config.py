import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# MongoDB configurations
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "trading_analyzer_db")

# API Keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Assets defaults - Primary focus on BTC, ETH, XAUT (Tether Gold)
DEFAULT_CRYPTO_SYMBOLS = ["BTC/USDT", "ETH/USDT", "XAUT/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT", "ADA/USDT", "DOGE/USDT"]
DEFAULT_FO_SYMBOLS = ["^NSEI", "^NSEBANK", "RELIANCE.NS", "AAPL", "SPY", "QQQ", "NVDA", "TSLA"]

# Timeframes & Settings
DEFAULT_TIMEFRAME = "1h"
SUPPORTED_TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]

# Storage folders
DATA_CACHE_DIR = BASE_DIR / "data_cache"
MODEL_DIR = BASE_DIR / "models"

# Create directories if they do not exist
DATA_CACHE_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

# Risk Settings
DEFAULT_ACCOUNT_BALANCE = float(os.getenv("DEFAULT_ACCOUNT_BALANCE", "10000.0"))
DEFAULT_RISK_PERCENT = float(os.getenv("DEFAULT_RISK_PERCENT", "1.0"))  # 1% per trade
DEFAULT_LEVERAGE = float(os.getenv("DEFAULT_LEVERAGE", "1.0"))


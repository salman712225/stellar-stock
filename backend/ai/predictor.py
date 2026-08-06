import logging
import pandas as pd
from typing import Dict, Any
from ai.train import train_model
from ai.inference import predict_latest
from config import MODEL_DIR

logger = logging.getLogger("predictor")

class MarketPredictor:
    def __init__(self):
        pass

    def model_exists(self, symbol: str) -> bool:
        clean_symbol = symbol.replace("/", "_").replace("^", "IDX_")
        model_path = MODEL_DIR / f"{clean_symbol}_rf.pkl"
        return model_path.exists()

    async def get_prediction(
        self, 
        df: pd.DataFrame, 
        symbol: str, 
        sentiment_score: float = 0.0,
        options_metrics: dict = None
    ) -> Dict[str, Any]:
        """
        Retrieves prediction for symbol. If model does not exist,
        triggers automatic quick training first.
        """
        if df.empty or len(df) < 50:
            return {
                "signal": "HOLD",
                "confidence": 0.5,
                "method": "insufficient_data"
            }

        # Train model if missing
        if not self.model_exists(symbol):
            logger.info(f"Model not found for {symbol}. Triggering auto-training.")
            train_res = train_model(df, symbol, sentiment_score, options_metrics)
            logger.info(f"Auto-training result: {train_res}")

        # Run prediction
        prediction = predict_latest(df, symbol, sentiment_score, options_metrics)
        return prediction

# Singleton
market_predictor = MarketPredictor()

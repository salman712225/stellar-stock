import pickle
import logging
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from config import MODEL_DIR
from ai.feature_engineering import extract_features

logger = logging.getLogger("ai_train")

def train_model(
    df: pd.DataFrame, 
    symbol: str, 
    sentiment_score: float = 0.0,
    options_metrics: dict = None
) -> dict:
    """
    Train a Random Forest Classifier on historical data to predict
    if the next bar will close up (1) or down/flat (0).
    Saves model as pickle.
    """
    if len(df) < 100:
        return {"success": False, "message": "Insufficient data to train. Need at least 100 bars."}

    try:
        # Extract features and targets
        X, y = extract_features(df, sentiment_score, options_metrics)
        
        if X.empty or y is None:
            return {"success": False, "message": "Failed to engineer features."}

        # Align X and y by dropping the last row (target is NaN for last candle)
        X_train_full = X.iloc[:-1]
        y_train_full = y.iloc[:-1]

        # Handle any outstanding NaN values in features
        X_train_full = X_train_full.fillna(0)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_train_full, y_train_full, test_size=0.2, random_state=42, shuffle=False
        )

        # Initialize and fit lightweight model (low memory footprint, single thread)
        model = RandomForestClassifier(n_estimators=15, max_depth=4, random_state=42, n_jobs=1)
        model.fit(X_train, y_train)

        # Evaluate model
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Save model to disk
        clean_symbol = symbol.replace("/", "_").replace("^", "IDX_")
        model_path = MODEL_DIR / f"{clean_symbol}_rf.pkl"
        
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        # Free temporary training memory
        del X_train, X_test, y_train, y_test, X_train_full, y_train_full, X, y
        import gc
        gc.collect()

        logger.info(f"Model trained for {symbol} with test accuracy {accuracy:.4f}")
        
        return {
            "success": True,
            "message": f"Successfully trained model for {symbol}.",
            "accuracy": round(float(accuracy), 4),
            "test_size": len(y_test),
            "model_path": str(model_path)
        }
    except Exception as e:
        logger.error(f"Error training model for {symbol}: {e}")
        return {"success": False, "message": f"Error: {e}"}

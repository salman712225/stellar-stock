import pandas as pd
from typing import Dict, Any, Tuple

class BaseStrategy:
    def __init__(self, name: str = "Base Strategy"):
        self.name = name

    def generate_signals(self, df: pd.DataFrame, smc_data: Dict[str, Any], sentiment_score: float = 0.0) -> pd.Series:
        """
        Generates buy (1), sell (-1), or hold (0) signals for the DataFrame.
        """
        raise NotImplementedError("Must implement generate_signals method")

class SMCMomentumStrategy(BaseStrategy):
    """
    SMC + Momentum + Sentiment Strategy:
    - BUY when:
      1. Supertrend is bullish (direction == 1) OR EMA(9) > EMA(21).
      2. Price hits/tests a bullish Order Block OR we break structure bullishly.
      3. RSI is not overbought (< 70).
      4. News sentiment is positive (sentiment_score >= 0.05).
    - SELL when:
      1. Supertrend is bearish (direction == -1) OR EMA(9) < EMA(21).
      2. Price hits a bearish Order Block OR breaks structure bearishly.
      3. RSI is not oversold (> 30).
      4. News sentiment is negative (sentiment_score <= -0.05).
    """
    def __init__(self, rsi_upper: float = 70.0, rsi_lower: float = 30.0):
        super().__init__("SMC Momentum Strategy")
        self.rsi_upper = rsi_upper
        self.rsi_lower = rsi_lower

    def generate_signals(self, df: pd.DataFrame, smc_data: Dict[str, Any], sentiment_score: float = 0.0) -> pd.Series:
        signals = pd.Series(0, index=df.index)
        if df.empty or len(df) < 20:
            return signals

        # Parse SMC levels
        unmit_bullish_ob = [ob for ob in smc_data.get("order_blocks", []) if ob["type"] == "bullish_ob" and not ob.get("mitigated")]
        unmit_bearish_ob = [ob for ob in smc_data.get("order_blocks", []) if ob["type"] == "bearish_ob" and not ob.get("mitigated")]
        
        bullish_ob_lows = [ob["low"] for ob in unmit_bullish_ob]
        bearish_ob_highs = [ob["high"] for ob in unmit_bearish_ob]
        
        closes = df["close"].values
        lows = df["low"].values
        highs = df["high"].values
        rsis = df["rsi_14"].values
        directions = df["direction"].values
        ema9 = df["ema_9"].values
        ema21 = df["ema_21"].values

        for i in range(1, len(df)):
            close_val = closes[i]
            low_val = lows[i]
            high_val = highs[i]
            rsi_val = rsis[i]
            dir_val = directions[i]
            e9_val = ema9[i]
            e21_val = ema21[i]

            # 1. Bullish Trigger
            # Check if price dipped into a bullish Order Block support
            touching_ob_support = False
            for ob_low in bullish_ob_lows:
                # Price dipped into range [ob_low, ob_low * 1.015]
                if low_val <= ob_low * 1.015 and close_val >= ob_low:
                    touching_ob_support = True
                    break

            bullish_indicators = (dir_val == 1) or (e9_val > e21_val)
            bullish_momentum = rsi_val < self.rsi_upper and rsi_val > 45
            bullish_sentiment = sentiment_score >= 0.05
            
            if bullish_indicators and (touching_ob_support or dir_val == 1) and bullish_momentum and bullish_sentiment:
                signals.iloc[i] = 1 # BUY

            # 2. Bearish Trigger
            # Check if price tested a bearish Order Block resistance
            touching_ob_resistance = False
            for ob_high in bearish_ob_highs:
                if high_val >= ob_high * 0.985 and close_val <= ob_high:
                    touching_ob_resistance = True
                    break

            bearish_indicators = (dir_val == -1) or (e9_val < e21_val)
            bearish_momentum = rsi_val > self.rsi_lower and rsi_val < 55
            bearish_sentiment = sentiment_score <= -0.05

            if bearish_indicators and (touching_ob_resistance or dir_val == -1) and bearish_momentum and bearish_sentiment:
                signals.iloc[i] = -1 # SELL
                
        return signals

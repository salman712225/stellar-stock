import pandas as pd
import numpy as np

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    close = df["close"]
    delta = close.diff()
    
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi

def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    """
    Calculate Stochastic Oscillator (%K and %D).
    """
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    
    k = 100.0 * ((df["close"] - low_min) / (high_max - low_min + 1e-10))
    d = k.rolling(window=d_period).mean()
    
    return pd.DataFrame({
        "stoch_k": k,
        "stoch_d": d
    }, index=df.index)

def calculate_stoch_rsi(df: pd.DataFrame, rsi_period: int = 14, stoch_period: int = 14, k_period: int = 3, d_period: int = 3) -> pd.DataFrame:
    """
    Calculate Stochastic RSI (%K and %D).
    """
    rsi = calculate_rsi(df, rsi_period)
    rsi_min = rsi.rolling(window=stoch_period).min()
    rsi_max = rsi.rolling(window=stoch_period).max()
    
    stoch_rsi_k = 100.0 * ((rsi - rsi_min) / (rsi_max - rsi_min + 1e-10))
    stoch_rsi_d = stoch_rsi_k.rolling(window=d_period).mean()
    
    return pd.DataFrame({
        "stoch_rsi_k": stoch_rsi_k,
        "stoch_rsi_d": stoch_rsi_d
    }, index=df.index)

def calculate_williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Williams %R (-100 to 0).
    """
    highest_high = df["high"].rolling(window=period).max()
    lowest_low = df["low"].rolling(window=period).min()
    wr = -100.0 * ((highest_high - df["close"]) / (highest_high - lowest_low + 1e-10))
    return wr

def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Money Flow Index (MFI) - volume-weighted RSI.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    money_flow = typical_price * df["volume"]
    
    tp_diff = typical_price.diff()
    pos_flow = np.where(tp_diff > 0, money_flow, 0.0)
    neg_flow = np.where(tp_diff < 0, money_flow, 0.0)
    
    pos_mf = pd.Series(pos_flow, index=df.index).rolling(window=period).sum()
    neg_mf = pd.Series(neg_flow, index=df.index).rolling(window=period).sum()
    
    mfi_ratio = pos_mf / (neg_mf + 1e-10)
    mfi = 100.0 - (100.0 / (1.0 + mfi_ratio))
    return mfi

def calculate_ultimate_oscillator(df: pd.DataFrame, period1: int = 7, period2: int = 14, period3: int = 28) -> pd.Series:
    """
    Calculate Ultimate Oscillator (multi-timeframe 7/14/28).
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    
    true_low = pd.concat([low, prev_close], axis=1).min(axis=1)
    true_high = pd.concat([high, prev_close], axis=1).max(axis=1)
    
    bp = close - true_low  # Buying Pressure
    tr = true_high - true_low  # True Range
    
    avg7 = bp.rolling(window=period1).sum() / (tr.rolling(window=period1).sum() + 1e-10)
    avg14 = bp.rolling(window=period2).sum() / (tr.rolling(window=period2).sum() + 1e-10)
    avg28 = bp.rolling(window=period3).sum() / (tr.rolling(window=period3).sum() + 1e-10)
    
    uo = 100.0 * ((4.0 * avg7 + 2.0 * avg14 + avg28) / 7.0)
    return uo

def calculate_roc(df: pd.DataFrame, period: int = 12) -> pd.Series:
    """Calculate Rate of Change (ROC)."""
    close = df["close"]
    prev_close = close.shift(period)
    roc = ((close - prev_close) / (prev_close + 1e-10)) * 100.0
    return roc

def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate Commodity Channel Index (CCI)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    tp_sma = tp.rolling(window=period).mean()
    
    def mad(x):
        return np.abs(x - x.mean()).mean()
        
    tp_mad = tp.rolling(window=period).apply(mad, raw=True)
    cci = (tp - tp_sma) / (0.015 * tp_mad + 1e-10)
    return cci

def detect_rsi_divergence(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    """
    Detect regular Bullish (Lower price low, higher RSI low) and Bearish (Higher price high, lower RSI high) divergences.
    """
    bull_div = pd.Series(False, index=df.index)
    bear_div = pd.Series(False, index=df.index)
    
    if "rsi_14" not in df.columns or len(df) < lookback + 5:
        return pd.DataFrame({"bullish_divergence": bull_div, "bearish_divergence": bear_div}, index=df.index)
        
    close = df["close"].values
    rsi = df["rsi_14"].values
    
    for i in range(lookback, len(df)):
        # Recent window
        window_close = close[i-lookback:i+1]
        window_rsi = rsi[i-lookback:i+1]
        
        # Check Bullish Divergence (price makes lower low, RSI makes higher low in oversold < 40)
        curr_price = window_close[-1]
        min_price_idx = np.argmin(window_close[:-1])
        if curr_price < window_close[min_price_idx] and window_rsi[-1] > window_rsi[min_price_idx] and window_rsi[-1] < 45:
            bull_div.iloc[i] = True
            
        # Check Bearish Divergence (price makes higher high, RSI makes lower high in overbought > 60)
        max_price_idx = np.argmax(window_close[:-1])
        if curr_price > window_close[max_price_idx] and window_rsi[-1] < window_rsi[max_price_idx] and window_rsi[-1] > 55:
            bear_div.iloc[i] = True
            
    return pd.DataFrame({"bullish_divergence": bull_div, "bearish_divergence": bear_div}, index=df.index)

def add_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all momentum indicators to the DataFrame."""
    d = df.copy()
    d["rsi_14"] = calculate_rsi(d, 14)
    d["rsi_7"] = calculate_rsi(d, 7)
    
    stoch_df = calculate_stochastic(d)
    d = pd.concat([d, stoch_df], axis=1)
    
    stoch_rsi_df = calculate_stoch_rsi(d)
    d = pd.concat([d, stoch_rsi_df], axis=1)
    
    d["williams_r"] = calculate_williams_r(d)
    d["mfi_14"] = calculate_mfi(d)
    d["ultimate_oscillator"] = calculate_ultimate_oscillator(d)
    d["roc_12"] = calculate_roc(d)
    d["cci_20"] = calculate_cci(d)
    
    div_df = detect_rsi_divergence(d)
    d = pd.concat([d, div_df], axis=1)
    return d


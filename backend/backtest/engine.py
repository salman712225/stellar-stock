import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from risk.position_size import calculate_position_size
from risk.stoploss import calculate_atr_stoploss
from backtest.strategy import BaseStrategy

class BacktestEngine:
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.0006):
        self.initial_capital = initial_capital
        self.commission = commission  # e.g., 0.06% exchange fee

    def run_backtest(
        self,
        df: pd.DataFrame,
        strategy: BaseStrategy,
        smc_data: Dict[str, Any],
        sentiment_score: float = 0.0,
        risk_percent: float = 1.0,
        leverage: float = 1.0,
        risk_reward_ratio: float = 2.0
    ) -> Dict[str, Any]:
        """
        Runs an event-driven backtest simulation.
        """
        if df.empty or len(df) < 20:
            return {"trades": [], "equity_curve": [], "metrics": {}}

        # Generate strategy signals
        signals = strategy.generate_signals(df, smc_data, sentiment_score)
        
        # Prepare list for trade logs
        trades = []
        equity_curve = []
        
        capital = self.initial_capital
        active_position = None  # None or Dict representing active trade
        
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        atrs = df["atr_14"].values
        timestamps = df["timestamp"].values
        
        for i in range(len(df)):
            close_price = closes[i]
            high_price = highs[i]
            low_price = lows[i]
            timestamp = int(timestamps[i])
            atr_val = atrs[i] if not np.isnan(atrs[i]) else (close_price * 0.02)
            signal = signals.iloc[i]
            
            # Check Stop Loss or Take Profit if position is active
            if active_position is not None:
                pos_type = active_position["type"]
                entry_price = active_position["entry_price"]
                sl = active_position["stop_loss"]
                tp = active_position["take_profit"]
                units = active_position["units"]
                
                exit_price = None
                exit_reason = None
                
                if pos_type == "long":
                    # Check if stop loss was hit
                    if low_price <= sl:
                        exit_price = sl
                        exit_reason = "Stop Loss"
                    # Check if take profit was hit
                    elif high_price >= tp:
                        exit_price = tp
                        exit_reason = "Take Profit"
                    # Check if reversal signal occurs
                    elif signal == -1:
                        exit_price = close_price
                        exit_reason = "Reversal"
                else: # short
                    if high_price >= sl:
                        exit_price = sl
                        exit_reason = "Stop Loss"
                    elif low_price <= tp:
                        exit_price = tp
                        exit_reason = "Take Profit"
                    elif signal == 1:
                        exit_price = close_price
                        exit_reason = "Reversal"
                        
                if exit_price is not None:
                    # Close position
                    raw_pnl = (exit_price - entry_price) * units if pos_type == "long" else (entry_price - exit_price) * units
                    fee = (entry_price * units * self.commission) + (exit_price * units * self.commission)
                    net_pnl = raw_pnl - fee
                    
                    capital += net_pnl
                    
                    trades.append({
                        "type": pos_type,
                        "entry_idx": active_position["entry_idx"],
                        "entry_time": active_position["entry_time"],
                        "entry_price": entry_price,
                        "exit_idx": i,
                        "exit_time": timestamp,
                        "exit_price": exit_price,
                        "units": units,
                        "raw_pnl": round(raw_pnl, 2),
                        "fee": round(fee, 2),
                        "net_pnl": round(net_pnl, 2),
                        "reason": exit_reason,
                        "capital_after": round(capital, 2)
                    })
                    
                    active_position = None
            
            # Check for entries if no position is active
            if active_position is None and signal != 0:
                pos_type = "long" if signal == 1 else "short"
                
                # Determine Stop Loss using ATR (e.g. 2 ATR away)
                sl_dist = 2.0 * atr_val
                sl = close_price - sl_dist if pos_type == "long" else close_price + sl_dist
                tp = close_price + (sl_dist * risk_reward_ratio) if pos_type == "long" else close_price - (sl_dist * risk_reward_ratio)
                
                # Calculate size using risk rules
                size_info = calculate_position_size(capital, risk_percent, close_price, sl, leverage)
                units = size_info.get("units", 0.0)
                
                if units > 0:
                    active_position = {
                        "type": pos_type,
                        "entry_idx": i,
                        "entry_time": timestamp,
                        "entry_price": close_price,
                        "stop_loss": sl,
                        "take_profit": tp,
                        "units": units
                    }
                    
            # Log current equity
            current_value = capital
            if active_position is not None:
                # Calculate current float valuation
                pos_type = active_position["type"]
                entry_p = active_position["entry_price"]
                u = active_position["units"]
                float_pnl = (close_price - entry_p) * u if pos_type == "long" else (entry_p - close_price) * u
                current_value += float_pnl
                
            equity_curve.append({
                "timestamp": timestamp,
                "equity": round(current_value, 2)
            })

        return {
            "initial_capital": self.initial_capital,
            "final_capital": round(capital, 2),
            "trades": trades,
            "equity_curve": equity_curve
        }

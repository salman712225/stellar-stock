import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_backtest_metrics(trades: List[Dict[str, Any]], equity_curve: List[Dict[str, Any]], initial_capital: float) -> Dict[str, Any]:
    """
    Calculate performance metrics for the completed backtest.
    """
    if not equity_curve:
        return {}

    # Extract final equity and compute return
    equity_series = pd.Series([eq["equity"] for eq in equity_curve])
    final_equity = equity_series.iloc[-1]
    total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100.0
    
    # Calculate Drawdown
    rolling_max = equity_series.cummax()
    drawdowns = (equity_series - rolling_max) / rolling_max * 100.0
    max_dd = drawdowns.min() # negative value

    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_return_pct": round(total_return_pct, 2),
            "final_equity": round(final_equity, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "avg_trade_pnl": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0
        }

    # Trade outcomes
    pnl_list = [t["net_pnl"] for t in trades]
    winning_trades = [p for p in pnl_list if p > 0]
    losing_trades = [p for p in pnl_list if p < 0]
    
    win_rate = (len(winning_trades) / total_trades) * 100.0
    
    gross_profits = sum(winning_trades)
    gross_losses = abs(sum(losing_trades))
    
    profit_factor = gross_profits / gross_losses if gross_losses > 0 else (gross_profits if gross_profits > 0 else 1.0)
    avg_trade_pnl = sum(pnl_list) / total_trades

    # Sharpe & Sortino Ratios (approximated from equity curve returns)
    eq_returns = equity_series.pct_change().dropna()
    if len(eq_returns) > 1 and eq_returns.std() > 0:
        # Assuming daily intervals, annualized (252 days)
        # For simplicity, calculate base average return / std dev
        avg_ret = eq_returns.mean()
        std_ret = eq_returns.std()
        
        # Risk-free rate assumed as 0 for simplicity
        sharpe = (avg_ret / std_ret) * np.sqrt(252)
        
        # Sortino (standard deviation of negative returns only)
        neg_returns = eq_returns[eq_returns < 0]
        neg_std = neg_returns.std() if len(neg_returns) > 1 else std_ret
        sortino = (avg_ret / neg_std) * np.sqrt(252) if neg_std > 0 else 0.0
    else:
        sharpe = 0.0
        sortino = 0.0

    return {
        "total_return_pct": round(total_return_pct, 2),
        "final_equity": round(final_equity, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "total_trades": total_trades,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_trade_pnl": round(avg_trade_pnl, 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "sortino_ratio": round(float(sortino), 2),
        "wins_count": len(winning_trades),
        "losses_count": len(losing_trades)
    }

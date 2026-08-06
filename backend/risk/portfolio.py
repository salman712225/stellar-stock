import pandas as pd
import numpy as np
from typing import Dict, Any, List

class PortfolioRiskManager:
    def __init__(self, max_exposure_pct: float = 50.0, max_correlation: float = 0.70):
        self.max_exposure_pct = max_exposure_pct
        self.max_correlation = max_correlation

    def calculate_correlations(self, asset_price_history: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Calculate correlation matrix for a dictionary of asset close price series.
        """
        if not asset_price_history or len(asset_price_history) < 2:
            return pd.DataFrame()
            
        df = pd.DataFrame(asset_price_history)
        # Compute daily returns
        returns_df = df.pct_change().dropna()
        return returns_df.corr()

    def check_portfolio_risk(
        self,
        positions: List[Dict[str, Any]],
        account_balance: float,
        correlations: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Scans current open positions to check exposure.
        Positions is a list of dicts: {'symbol': str, 'value': float, 'direction': str}
        """
        total_exposure = sum(pos["value"] for pos in positions)
        exposure_pct = (total_exposure / account_balance) * 100.0 if account_balance > 0 else 0.0
        
        warnings = []
        if exposure_pct > self.max_exposure_pct:
            warnings.append(f"Total portfolio exposure is high: {exposure_pct:.1f}% (Max: {self.max_exposure_pct}%)")
            
        # Check for correlation risk
        high_corr_pairs = []
        if not correlations.empty:
            symbols = list(correlations.columns)
            for i in range(len(symbols)):
                for j in range(i+1, len(symbols)):
                    s1, s2 = symbols[i], symbols[j]
                    corr_val = correlations.loc[s1, s2]
                    if abs(corr_val) > self.max_correlation:
                        high_corr_pairs.append((s1, s2, round(corr_val, 2)))
                        
        # Check active positions for highly correlated assets
        active_symbols = [pos["symbol"] for pos in positions]
        for s1, s2, corr in high_corr_pairs:
            if s1 in active_symbols and s2 in active_symbols:
                warnings.append(f"High risk correlation between open positions {s1} and {s2}: Correlation={corr}")

        return {
            "total_exposure_value": round(total_exposure, 2),
            "exposure_pct": round(exposure_pct, 2),
            "warnings": warnings,
            "status": "SAFE" if not warnings else "WARNING",
            "high_correlation_pairs": high_corr_pairs
        }

# Singleton
portfolio_risk_manager = PortfolioRiskManager()

import logging

logger = logging.getLogger("risk_sizing")

def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss: float,
    leverage: float = 1.0
) -> dict:
    """
    Calculate the risk-adjusted position size.
    Formula:
        Total Capital at Risk = Account Balance * (Risk Percent / 100)
        Risk Per Unit = | Entry Price - Stop Loss |
        Position Size (Units) = Total Capital at Risk / Risk Per Unit
        Position Value = Position Size * Entry Price
        Margin Required = Position Value / Leverage
    """
    if account_balance <= 0:
        return {"units": 0.0, "value": 0.0, "error": "Account balance must be positive"}
    if risk_percent <= 0 or risk_percent > 100:
        return {"units": 0.0, "value": 0.0, "error": "Risk percent must be between 0 and 100"}
    if entry_price <= 0:
        return {"units": 0.0, "value": 0.0, "error": "Entry price must be positive"}
    if stop_loss <= 0:
        return {"units": 0.0, "value": 0.0, "error": "Stop loss must be positive"}
        
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit == 0:
        return {"units": 0.0, "value": 0.0, "error": "Stop loss cannot equal entry price"}

    capital_at_risk = account_balance * (risk_percent / 100.0)
    units = capital_at_risk / risk_per_unit
    
    # Cap position value to account size * leverage
    max_position_value = account_balance * leverage
    position_value = units * entry_price
    
    if position_value > max_position_value:
        units = max_position_value / entry_price
        position_value = max_position_value
        capital_at_risk = units * risk_per_unit
        warning = "Position size capped by max account purchasing power"
    else:
        warning = None

    margin_required = position_value / leverage

    return {
        "capital_at_risk": round(capital_at_risk, 2),
        "units": round(units, 4),
        "position_value": round(position_value, 2),
        "margin_required": round(margin_required, 2),
        "risk_per_unit": round(risk_per_unit, 4),
        "warning": warning
    }

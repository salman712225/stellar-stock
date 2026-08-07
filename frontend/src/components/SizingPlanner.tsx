import React from "react";
import { Calculator } from "lucide-react";

interface SizingPlannerProps {
  balance: number;
  setBalance: (v: number) => void;
  riskPercent: number;
  setRiskPercent: (v: number) => void;
  leverage: number;
  setLeverage: (v: number) => void;
  rrRatio: number;
  setRrRatio: (v: number) => void;
  calcEntry: number;
  setCalcEntry: (v: number) => void;
  calcSL: number;
  setCalcSL: (v: number) => void;
  calcResult: any;
}

export const SizingPlanner: React.FC<SizingPlannerProps> = ({
  balance,
  setBalance,
  riskPercent,
  setRiskPercent,
  leverage,
  setLeverage,
  rrRatio,
  setRrRatio,
  calcEntry,
  setCalcEntry,
  calcSL,
  setCalcSL,
  calcResult,
}) => {
  return (
    <div className="tv-panel sizing-planner-card">
      <div className="tv-panel-header">
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Calculator size={14} /> Capital Sizing Planner
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {/* Row 1: Account Balance & Risk % */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
          <div className="form-group">
            <label>Balance ($)</label>
            <input
              type="number"
              className="form-input"
              value={balance}
              onChange={(e) => setBalance(parseFloat(e.target.value) || 0)}
            />
          </div>
          <div className="form-group">
            <label>Max Risk: {riskPercent}%</label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="5.0"
              className="form-input"
              value={riskPercent}
              onChange={(e) => setRiskPercent(parseFloat(e.target.value) || 1.0)}
            />
          </div>
        </div>

        {/* Row 2: Leverage & R:R Ratio */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
          <div className="form-group">
            <label>Leverage Factor (x)</label>
            <input
              type="number"
              className="form-input"
              value={leverage}
              onChange={(e) => setLeverage(parseFloat(e.target.value) || 1.0)}
            />
          </div>
          <div className="form-group">
            <label>Target R:R Ratio</label>
            <input
              type="number"
              step="0.1"
              className="form-input"
              value={rrRatio}
              onChange={(e) => setRrRatio(parseFloat(e.target.value) || 2.0)}
            />
          </div>
        </div>

        {/* Row 3: Trade Entry & Stop Loss */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
          <div className="form-group">
            <label>Entry Price ($)</label>
            <input
              type="number"
              step="any"
              className="form-input"
              value={calcEntry}
              onChange={(e) => setCalcEntry(parseFloat(e.target.value) || 0)}
            />
          </div>
          <div className="form-group">
            <label>Stop Loss ($)</label>
            <input
              type="number"
              step="any"
              className="form-input"
              value={calcSL}
              onChange={(e) => setCalcSL(parseFloat(e.target.value) || 0)}
            />
          </div>
        </div>

        {/* Dynamic calculations result layout */}
        {calcResult ? (
          <div
            style={{
              marginTop: "4px",
              paddingTop: "12px",
              borderTop: "1px solid #2a2e39",
              display: "flex",
              flexDirection: "column",
              gap: "6px",
              fontSize: "12px",
            }}
          >
            <div className="p-flex-between">
              <span style={{ color: "#787b86" }}>Risk per Unit:</span>
              <strong>${calcResult.riskPerUnit.toFixed(2)}</strong>
            </div>
            <div className="p-flex-between">
              <span style={{ color: "#787b86" }}>Total Cash at Risk:</span>
              <strong style={{ color: "#f23645" }}>${calcResult.capitalAtRisk.toFixed(2)}</strong>
            </div>
            <div className="p-flex-between">
              <span style={{ color: "#787b86" }}>Calculated Units:</span>
              <strong>{calcResult.units.toFixed(4)}</strong>
            </div>
            <div className="p-flex-between">
              <span style={{ color: "#787b86" }}>Margin Required:</span>
              <strong style={{ color: "#089981" }}>${calcResult.marginRequired.toFixed(2)}</strong>
            </div>
            <div className="p-flex-between">
              <span style={{ color: "#787b86" }}>Purchase Value:</span>
              <strong>${calcResult.purchaseValue.toFixed(2)}</strong>
            </div>
          </div>
        ) : (
          <div style={{ color: "#787b86", fontSize: "11px", textAlign: "center", padding: "6px 0" }}>
            Adjust Entry & Stop Loss to view sizing calculations.
          </div>
        )}
      </div>
    </div>
  );
};

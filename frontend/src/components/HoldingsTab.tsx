import React from "react";
import { RefreshCw, Trash2, CheckCircle2, ShieldAlert } from "lucide-react";

interface Position {
  id: number;
  symbol: string;
  type: "long" | "short" | "call" | "put";
  strike: number | null;
  entry: number;
  limit: number;
  sl: number;
  timeframe: string;
}

interface HoldingsTabProps {
  trackedPositions: Position[];
  evaluationResults: Record<number, any>;
  evaluatingAll: boolean;
  evaluateAllPositions: () => void;
  handleRemovePosition: (id: number) => void;
  addPositionForm: React.ReactNode;
}

export const HoldingsTab: React.FC<HoldingsTabProps> = ({
  trackedPositions,
  evaluationResults,
  evaluatingAll,
  evaluateAllPositions,
  handleRemovePosition,
  addPositionForm,
}) => {
  return (
    <div className="workspace-content">
      <div className="split-layout">
        {/* Left Side: Tracked positions list */}
        <div className="split-left">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "16px",
            }}
          >
            <h3 style={{ margin: 0, color: "#f0f3fa", fontSize: "16px", fontWeight: 600 }}>
              Tracked Holdings Portfolio
            </h3>
            <button
              className="btn-secondary"
              onClick={evaluateAllPositions}
              disabled={evaluatingAll}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <RefreshCw size={12} className={evaluatingAll ? "spin" : ""} />
              Re-evaluate Holdings
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {trackedPositions.length === 0 ? (
              <div className="tv-panel" style={{ textAlign: "center", color: "#787b86", padding: "40px" }}>
                No holdings currently tracked. Use the right form to register active positions!
              </div>
            ) : (
              trackedPositions.map((pos) => {
                const evalRes = evaluationResults[pos.id];
                const advice = evalRes?.simple_advice || "Keep it";

                return (
                  <div key={pos.id} className="tv-panel" style={{ position: "relative", marginBottom: 0 }}>
                    {/* Glowing Advice Banner */}
                    {evalRes ? (
                      advice === "Keep it" ? (
                        <div className="glowing-card-keep">
                          <h4
                            style={{
                              margin: 0,
                              fontSize: "14px",
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                              fontWeight: 600,
                            }}
                          >
                            <CheckCircle2 size={16} /> DIRECTIVE: KEEP IT (📈 Predict Rise / Continuation)
                          </h4>
                        </div>
                      ) : (
                        <div className="glowing-card-sell">
                          <h4
                            style={{
                              margin: 0,
                              fontSize: "14px",
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                              fontWeight: 600,
                            }}
                          >
                            <ShieldAlert size={16} /> DIRECTIVE: SELL IT (📉 Predict Drop / Risk Exit)
                          </h4>
                        </div>
                      )
                    ) : (
                      <div
                        style={{
                          backgroundColor: "#1c2030",
                          padding: "10px",
                          borderRadius: "6px",
                          color: "#787b86",
                          marginBottom: "12px",
                          fontSize: "12px",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                        }}
                      >
                        <RefreshCw size={12} className="spin" /> Evaluating active pricing...
                      </div>
                    )}

                    {/* Position Details Header */}
                    <div
                      className="p-flex-between"
                      style={{
                        borderBottom: "1px solid #2a2e39",
                        paddingBottom: "10px",
                        marginBottom: "12px",
                      }}
                    >
                      <div>
                        <span
                          style={{
                            fontSize: "16px",
                            fontWeight: 700,
                            color: "#f0f3fa",
                            marginRight: "8px",
                          }}
                        >
                          {pos.symbol}
                        </span>
                        <span
                          className={
                            pos.type === "long" || pos.type === "call" ? "badge-buy" : "badge-sell"
                          }
                        >
                          {pos.type.toUpperCase()}
                        </span>
                        {pos.strike && (
                          <span style={{ color: "#787b86", fontSize: "11px", marginLeft: "10px" }}>
                            Strike: ${pos.strike}
                          </span>
                        )}
                      </div>
                      <button
                        className="btn-secondary"
                        style={{
                          color: "#f23645",
                          borderColor: "rgba(242, 54, 69, 0.2)",
                          display: "flex",
                          alignItems: "center",
                          padding: "4px 8px",
                          gap: "4px",
                        }}
                        onClick={() => handleRemovePosition(pos.id)}
                      >
                        <Trash2 size={12} /> Delete
                      </button>
                    </div>

                    <div className="p-grid-2">
                      {/* Left: Position entry configuration details */}
                      <div style={{ fontSize: "13px", display: "flex", flexDirection: "column", gap: "6px" }}>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Entry Price:</span>
                          <strong>${pos.entry.toLocaleString()}</strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Limit Target:</span>
                          <strong>${pos.limit.toLocaleString()}</strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Stop Loss:</span>
                          <strong>${pos.sl.toLocaleString()}</strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Timeframe:</span>
                          <strong>{pos.timeframe}</strong>
                        </div>
                      </div>

                      {/* Right: Evaluator suggestions feedback */}
                      {evalRes && (
                        <div
                          style={{
                            fontSize: "13px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "6px",
                            borderLeft: "1px solid #2a2e39",
                            paddingLeft: "16px",
                          }}
                        >
                          <div className="p-flex-between">
                            <span style={{ color: "#787b86" }}>Current Spot:</span>
                            <strong>${evalRes.spot_price?.toLocaleString()}</strong>
                          </div>
                          <div className="p-flex-between">
                            <span style={{ color: "#787b86" }}>PnL Net:</span>
                            <strong style={{ color: evalRes.pnl_percentage >= 0 ? "#089981" : "#f23645" }}>
                              {evalRes.pnl_percentage >= 0 ? "+" : ""}
                              {evalRes.pnl_percentage}%
                            </strong>
                          </div>
                          <div className="p-flex-between">
                            <span style={{ color: "#787b86" }}>ML Alignment:</span>
                            <strong>{evalRes.ml_aligned ? "Aligned 🟢" : "Conflict ⚠️"}</strong>
                          </div>
                          <div
                            className="p-flex-between"
                            style={{ flexDirection: "column", alignItems: "flex-start", gap: "4px" }}
                          >
                            <span style={{ color: "#787b86" }}>Rationale:</span>
                            <p style={{ margin: 0, fontSize: "11px", color: "#d1d4dc", lineHeight: "1.4" }}>
                              {evalRes.rationale}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Side: Render the track position form passed as props */}
        <div className="split-right">{addPositionForm}</div>
      </div>
    </div>
  );
};

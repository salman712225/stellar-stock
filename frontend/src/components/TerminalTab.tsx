import React, { useState } from "react";
import { RefreshCw, Sparkles, Play, ChevronDown, ChevronUp } from "lucide-react";
import { TradingViewChart } from "./TradingViewChart";
import { ConsensusGauge } from "./ConsensusGauge";
import { SizingPlanner } from "./SizingPlanner";

interface TerminalTabProps {
  isLoading: boolean;
  errorMsg: string;
  analysisData: any;
  activeSymbol: string;
  timeframe: string;
  fetchAnalysis: (s: string, t: string) => void;
  cryptoPresets: string[];
  chainData: any;
  backtestMetrics: any;
  runningBacktest: boolean;
  runBacktest: () => void;
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

export const TerminalTab: React.FC<TerminalTabProps> = ({
  isLoading,
  errorMsg,
  analysisData,
  activeSymbol,
  timeframe,
  fetchAnalysis,
  cryptoPresets,
  chainData,
  backtestMetrics,
  runningBacktest,
  runBacktest,
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
  const [isReportExpanded, setIsReportExpanded] = useState(false);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "100px 0", color: "#787b86" }}>
        <RefreshCw className="spin" size={32} style={{ marginBottom: "10px" }} />
        <div>Fetching market structures, sentiment arrays, and ML models...</div>
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div
        style={{
          padding: "40px",
          backgroundColor: "rgba(242, 54, 69, 0.1)",
          borderRadius: "6px",
          border: "1px solid #f23645",
          color: "#f23645",
        }}
      >
        <strong>Error:</strong> {errorMsg}
        <button
          className="btn-primary"
          style={{ marginTop: "15px", width: "auto" }}
          onClick={() => fetchAnalysis(activeSymbol, timeframe)}
        >
          Retry Request
        </button>
      </div>
    );
  }

  if (!analysisData) {
    return (
      <div style={{ textAlign: "center", padding: "100px 0", color: "#787b86" }}>
        Select preset symbol on the left to pull live metrics.
      </div>
    );
  }

  // Consensus Gauge calculation
  const latest = analysisData.indicators?.latest || {};
  const sig = analysisData.prediction?.signal || "HOLD";
  const rsi = latest.rsi_14 || 50;
  const score = analysisData.sentiment?.score || 0;

  let rating = 50;
  if (latest.direction === 1) rating += 15; else rating -= 15;
  if (latest.range_direction === 1) rating += 15; else rating -= 15;
  if (rsi > 55) rating += 10; else if (rsi < 45) rating -= 10;
  if (latest.macd_hist > 0) rating += 10; else rating -= 10;
  if (score > 0.15) rating += 10; else if (score < -0.15) rating -= 10;
  if (sig === "BUY") rating += 20; else if (sig === "SELL") rating -= 20;

  rating = Math.max(5, Math.min(95, rating));
  let conLabel = "NEUTRAL";
  let conColor = "#787b86";

  if (rating >= 70) {
    conLabel = "STRONG BUY";
    conColor = "#089981";
  } else if (rating >= 55) {
    conLabel = "BUY";
    conColor = "#26a69a";
  } else if (rating <= 30) {
    conLabel = "STRONG SELL";
    conColor = "#f23645";
  } else if (rating <= 45) {
    conLabel = "SELL";
    conColor = "#ff5252";
  }

  const isCrypto = cryptoPresets.includes(activeSymbol);

  return (
    <div className="workspace-content">
      <div className="split-layout">
        {/* Left side: Interactive Candlestick charts & AI report */}
        <div className="split-left">
          {/* Chart Panel */}
          <div className="tv-panel" style={{ padding: "8px" }}>
            <div
              className="tv-panel-header"
              style={{ padding: "8px 12px 0 12px", borderBottom: "none" }}
            >
              <span>📈 PRICE CHART & RANGE FILTER OVERLAYS</span>
              <span style={{ color: "#787b86", fontSize: "10px" }}>Websocket Connected</span>
            </div>
            {analysisData.chart_data && (
              <TradingViewChart candles={analysisData.chart_data} symbol={activeSymbol} />
            )}
          </div>

          {/* AI report card - with toggle for user friendliness */}
          <div className="tv-panel">
            <div className="tv-panel-header" style={{ marginBottom: "6px" }}>
              <span>🧠 AI ANALYST RESEARCH LOG REPORT</span>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <span style={{ color: "#2962ff", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Sparkles size={11} /> Calibrated Forecast
                </span>
                <button
                  className="btn-secondary"
                  onClick={() => setIsReportExpanded((prev) => !prev)}
                  style={{
                    padding: "2px 6px",
                    fontSize: "10px",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  {isReportExpanded ? (
                    <>
                      <ChevronUp size={12} /> Collapse
                    </>
                  ) : (
                    <>
                      <ChevronDown size={12} /> Expand
                    </>
                  )}
                </button>
              </div>
            </div>

            <div
              className="report-markdown"
              style={{
                maxHeight: isReportExpanded ? "none" : "120px",
                overflowY: isReportExpanded ? "visible" : "hidden",
                position: "relative",
                transition: "max-height 0.2s ease-out",
              }}
            >
              <div
                dangerouslySetInnerHTML={{
                  __html: analysisData.report?.replace(/\n/g, "<br/>") || "",
                }}
              />
              {!isReportExpanded && (
                <div
                  style={{
                    position: "absolute",
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: "40px",
                    background: "linear-gradient(transparent, #131722)",
                    pointerEvents: "none",
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Right side: Scorecards, Calculator, Backtester */}
        <div className="split-right">
          {/* Technical consensus */}
          <div className="tv-panel" style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div className="tv-panel-header" style={{ width: "100%" }}>
              <span>🎯 Technical Consensus Speedometer</span>
            </div>
            <ConsensusGauge value={rating} label={conLabel} color={conColor} />
          </div>

          {/* Core specs scorecards */}
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span>📊 Asset Scorecards</span>
            </div>
            <div className="tv-scorecard">
              <div className="tv-scorecard-label">Last Traded Price</div>
              <div className="tv-scorecard-value">
                ${analysisData.current_price?.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 4,
                })}
              </div>
              <div className="tv-scorecard-sub">Active Feed Price</div>
            </div>

            <div className="tv-scorecard">
              <div className="tv-scorecard-label">AI Forecast (ML Calibrated)</div>
              <div style={{ marginTop: "4px" }}>
                <span
                  className={
                    analysisData.prediction?.signal === "BUY"
                      ? "badge-buy"
                      : analysisData.prediction?.signal === "SELL"
                      ? "badge-sell"
                      : "badge-hold"
                  }
                >
                  {analysisData.prediction?.signal || "HOLD"} (
                  {((analysisData.prediction?.confidence || 0.5) * 100).toFixed(0)}% Conv)
                </span>
              </div>
              <div className="tv-scorecard-sub">Next-period direction skew</div>
            </div>

            <div className="tv-scorecard">
              <div className="tv-scorecard-label">Overall Sentiment</div>
              <div style={{ marginTop: "4px" }}>
                <span
                  className={
                    analysisData.sentiment?.label === "bullish"
                      ? "badge-buy"
                      : analysisData.sentiment?.label === "bearish"
                      ? "badge-sell"
                      : "badge-hold"
                  }
                >
                  {analysisData.sentiment?.label?.toUpperCase() || "NEUTRAL"} ({analysisData.sentiment?.score})
                </span>
              </div>
              <div className="tv-scorecard-sub">News & forums aggregated sentiment</div>
            </div>
          </div>

          {/* Sizing Planner Widget */}
          <SizingPlanner
            balance={balance}
            setBalance={setBalance}
            riskPercent={riskPercent}
            setRiskPercent={setRiskPercent}
            leverage={leverage}
            setLeverage={setLeverage}
            rrRatio={rrRatio}
            setRrRatio={setRrRatio}
            calcEntry={calcEntry}
            setCalcEntry={setCalcEntry}
            calcSL={calcSL}
            setCalcSL={setCalcSL}
            calcResult={calcResult}
          />

          {/* Options derivatives details */}
          {!isCrypto && chainData && (
            <div className="tv-panel">
              <div className="tv-panel-header">
                <span>📊 ATM Options Chain</span>
              </div>
              <div style={{ fontSize: "11px", display: "flex", flexDirection: "column", gap: "6px" }}>
                <div className="p-flex-between">
                  <span style={{ color: "#787b86" }}>Put-Call Ratio (OI):</span>
                  <strong>{chainData.pcr_oi?.toFixed(2)}</strong>
                </div>
                <div className="p-flex-between">
                  <span style={{ color: "#787b86" }}>PCR (Volume):</span>
                  <strong>{chainData.pcr_volume?.toFixed(2)}</strong>
                </div>
                <div className="p-flex-between">
                  <span style={{ color: "#787b86" }}>Max Pain Strike:</span>
                  <strong style={{ color: "#FF9800" }}>${chainData.max_pain?.toFixed(2)}</strong>
                </div>
              </div>
            </div>
          )}

          {/* Backtest strategy simulator card */}
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span>🔄 Strategy Backtester Simulator</span>
            </div>
            <button
              className="btn-primary"
              onClick={runBacktest}
              disabled={runningBacktest}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
              }}
            >
              <Play size={13} fill="white" />{" "}
              {runningBacktest ? "Simulating Strategy..." : "Run SMC Backtest"}
            </button>

            {backtestMetrics && (
              <div
                style={{
                  marginTop: "12px",
                  borderTop: "1px solid #2a2e39",
                  paddingTop: "12px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                  fontSize: "12px",
                }}
              >
                <div className="p-flex-between">
                  <span style={{ color: "#787b86" }}>Win Rate:</span>
                  <strong style={{ color: "#089981" }}>{backtestMetrics.metrics?.win_rate_pct}%</strong>
                </div>
                <div className="p-flex-between">
                  <span style={{ color: "#787b86" }}>Net Return:</span>
                  <strong
                    style={{
                      color:
                        backtestMetrics.metrics?.total_return_pct >= 0 ? "#089981" : "#f23645",
                    }}
                  >
                    {backtestMetrics.metrics?.total_return_pct >= 0 ? "+" : ""}
                    {backtestMetrics.metrics?.total_return_pct}%
                  </strong>
                </div>
                <div className="p-flex-between">
                  <span style={{ color: "#787b86" }}>Profit Factor:</span>
                  <strong>{backtestMetrics.metrics?.profit_factor}</strong>
                </div>
                <div className="p-flex-between">
                  <span style={{ color: "#787b86" }}>Max Drawdown:</span>
                  <strong style={{ color: "#f23645" }}>
                    {backtestMetrics.metrics?.max_drawdown_pct}%
                  </strong>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

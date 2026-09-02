import React, { useState, useEffect } from "react";
import { RefreshCw, Sparkles, Play, ChevronDown, ChevronUp, Target, TrendingUp } from "lucide-react";
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
  const [mtfData, setMtfData] = useState<any>(null);

  // Fetch Multi-timeframe confluence on symbol change
  useEffect(() => {
    const fetchMtf = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/multi-timeframe?symbol=${encodeURIComponent(activeSymbol)}`);
        if (res.ok) {
          const data = await res.json();
          setMtfData(data);
        }
      } catch (err) {
        console.error("Failed to fetch MTF data:", err);
      }
    };
    fetchMtf();
  }, [activeSymbol]);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "100px 0", color: "#787b86" }}>
        <RefreshCw className="spin" size={32} style={{ marginBottom: "10px", color: "#2962ff" }} />
        <div style={{ fontSize: "14px", fontWeight: 600 }}>Calculating institutional SMC structures, momentum matrices, and AI forecasts for {activeSymbol}...</div>
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div
        style={{
          padding: "30px",
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
        Select preset symbol on the left to load real-time analytics.
      </div>
    );
  }

  const latest = analysisData.indicators?.latest || {};
  const sig = analysisData.prediction?.signal || "HOLD";
  const rsi = latest.rsi_14 || 50;
  const score = analysisData.sentiment?.score || 0;
  const currentPrice = analysisData.current_price || 0;
  const atr = latest.atr_14 || (currentPrice * 0.02);

  // Dynamic tactical calculations
  const stopLoss = sig === "BUY" ? currentPrice - (2.0 * atr) : currentPrice + (2.0 * atr);
  const tp1 = sig === "BUY" ? currentPrice + (1.5 * atr) : currentPrice - (1.5 * atr);
  const tp2 = sig === "BUY" ? currentPrice + (3.0 * atr) : currentPrice - (3.0 * atr);
  const tp3 = sig === "BUY" ? currentPrice + (5.0 * atr) : currentPrice - (5.0 * atr);
  const rr = (Math.abs(tp2 - currentPrice) / Math.max(1e-5, Math.abs(currentPrice - stopLoss))).toFixed(2);

  // Consensus Gauge calculation
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
        {/* LEFT COLUMN: Candlestick Chart & AI Report */}
        <div className="split-left">
          {/* Chart Panel */}
          <div className="tv-panel" style={{ padding: "8px" }}>
            <div
              className="tv-panel-header"
              style={{ padding: "6px 12px", borderBottom: "none" }}
            >
              <span>📈 {activeSymbol} REAL-TIME CANDLESTICK CHART</span>
              <span style={{ color: "#089981", fontSize: "11px", display: "flex", alignItems: "center", gap: "4px" }}>
                <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "#089981" }} /> Streaming Feed
              </span>
            </div>
            {analysisData.chart_data && (
              <TradingViewChart candles={analysisData.chart_data} symbol={activeSymbol} />
            )}
          </div>

          {/* Multi-Timeframe Matrix Confluence Bar */}
          {mtfData && mtfData.matrix && (
            <div className="tv-panel">
              <div className="tv-panel-header">
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <TrendingUp size={14} style={{ color: "#2962ff" }} /> Multi-Timeframe Confluence Matrix
                </span>
                <span style={{ color: mtfData.overall_confluence?.includes("BULLISH") ? "#089981" : mtfData.overall_confluence?.includes("BEARISH") ? "#f23645" : "#FF9800", fontWeight: 700, fontSize: "11px" }}>
                  {mtfData.overall_confluence} ({mtfData.bullish_percentage}% Bullish)
                </span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "8px", padding: "6px 0" }}>
                {["5m", "15m", "1h", "4h", "1d"].map((tf) => {
                  const m = mtfData.matrix[tf] || {};
                  const isBull = m.bias === "BULLISH";
                  const isBear = m.bias === "BEARISH";
                  return (
                    <div
                      key={tf}
                      style={{
                        backgroundColor: "#1e222d",
                        padding: "8px",
                        borderRadius: "4px",
                        textAlign: "center",
                        border: `1px solid ${isBull ? "rgba(8, 153, 129, 0.4)" : isBear ? "rgba(242, 54, 69, 0.4)" : "#2a2e39"}`
                      }}
                    >
                      <div style={{ fontSize: "11px", color: "#787b86", fontWeight: 700 }}>{tf.toUpperCase()}</div>
                      <div style={{ fontSize: "12px", fontWeight: "bold", margin: "4px 0", color: isBull ? "#089981" : isBear ? "#f23645" : "#787b86" }}>
                        {m.bias || "NEUTRAL"}
                      </div>
                      <div style={{ fontSize: "10px", color: "#50535e" }}>RSI: {m.rsi || 50}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* AI Institutional Research Dossier Preview */}
          <div className="tv-panel">
            <div className="tv-panel-header" style={{ marginBottom: "6px" }}>
              <span>🧠 AI QUANT RESEARCH DOSSIER SUMMARY</span>
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
                      <ChevronDown size={12} /> Expand Full Report
                    </>
                  )}
                </button>
              </div>
            </div>

            <div
              className="report-markdown"
              style={{
                maxHeight: isReportExpanded ? "none" : "140px",
                overflowY: isReportExpanded ? "visible" : "hidden",
                position: "relative",
                transition: "max-height 0.2s ease-out",
                fontSize: "12px"
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

        {/* RIGHT COLUMN: Speedometer, Scorecards, Tactical Plan, Sizing, Backtester */}
        <div className="split-right">
          {/* Technical consensus */}
          <div className="tv-panel" style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div className="tv-panel-header" style={{ width: "100%" }}>
              <span>🎯 Technical Consensus Speedometer</span>
            </div>
            <ConsensusGauge value={rating} label={conLabel} color={conColor} />
          </div>

          {/* Core Scorecards */}
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span>📊 Asset Metric Scorecards</span>
            </div>
            <div className="tv-scorecard">
              <div className="tv-scorecard-label">Last Traded Price</div>
              <div className="tv-scorecard-value">
                ${analysisData.current_price?.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 4,
                })}
              </div>
              <div className="tv-scorecard-sub">Active CCXT / Yahoo Live Price</div>
            </div>

            <div className="tv-scorecard">
              <div className="tv-scorecard-label">AI Directional Forecast</div>
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
                  {((analysisData.prediction?.confidence || 0.5) * 100).toFixed(0)}% Confidence)
                </span>
              </div>
              <div className="tv-scorecard-sub">Multi-feature machine learning classifier</div>
            </div>

            <div className="tv-scorecard">
              <div className="tv-scorecard-label">Market & News Sentiment</div>
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
                  {analysisData.sentiment?.label?.toUpperCase() || "NEUTRAL"} ({analysisData.sentiment?.score > 0 ? `+${analysisData.sentiment?.score}` : analysisData.sentiment?.score})
                </span>
              </div>
              <div className="tv-scorecard-sub">Fear & Greed Index: {analysisData.sentiment?.fear_greed?.score} ({analysisData.sentiment?.fear_greed?.label})</div>
            </div>
          </div>

          {/* Tactical Execution Blueprint */}
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Target size={14} style={{ color: "#2962ff" }} /> Tactical Execution Setup
              </span>
              <span style={{ fontSize: "11px", color: "#FFCA28" }}>R:R = 1:{rr}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px", padding: "4px 0" }}>
              <div className="p-flex-between">
                <span style={{ color: "#787b86" }}>Execution Entry:</span>
                <strong>${currentPrice.toLocaleString(undefined, { maximumFractionDigits: 4 })}</strong>
              </div>
              <div className="p-flex-between">
                <span style={{ color: "#787b86" }}>Stop Loss (SL):</span>
                <strong style={{ color: "#f23645" }}>${stopLoss.toLocaleString(undefined, { maximumFractionDigits: 4 })}</strong>
              </div>
              <div className="p-flex-between">
                <span style={{ color: "#787b86" }}>Take Profit 1 (TP1):</span>
                <strong style={{ color: "#089981" }}>${tp1.toLocaleString(undefined, { maximumFractionDigits: 4 })}</strong>
              </div>
              <div className="p-flex-between">
                <span style={{ color: "#787b86" }}>Take Profit 2 (TP2):</span>
                <strong style={{ color: "#00E676" }}>${tp2.toLocaleString(undefined, { maximumFractionDigits: 4 })}</strong>
              </div>
              <div className="p-flex-between">
                <span style={{ color: "#787b86" }}>Take Profit 3 (TP3):</span>
                <strong style={{ color: "#00B0FF" }}>${tp3.toLocaleString(undefined, { maximumFractionDigits: 4 })}</strong>
              </div>
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

          {/* Options derivatives details (if traditional asset) */}
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

          {/* Strategy Backtester card */}
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

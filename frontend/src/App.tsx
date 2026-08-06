import React, { useState, useEffect } from "react";
import { 
  TrendingUp, 
  Layers, 
  Calculator, 
  Play, 
  Plus, 
  Trash2, 
  RefreshCw, 
  Bell, 
  Sparkles,
  ArrowUpRight,
  ShieldAlert,
  Flame,
  CheckCircle2,
  FileText
} from "lucide-react";
import { TradingViewChart } from "./components/TradingViewChart";
import { ConsensusGauge } from "./components/ConsensusGauge";

// Interfaces
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

interface Alert {
  symbol: string;
  signal: "BUY" | "SELL";
  price: number;
  timestamp: string;
}

const API_URL = "http://localhost:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState<"terminal" | "holdings">("terminal");
  const [assetClass, setAssetClass] = useState<"Crypto" | "FO">("Crypto");
  const [activeSymbol, setActiveSymbol] = useState("BTC/USDT");
  const [customSymbol, setCustomSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("1h");

  // Default Sizing parameters
  const [balance, setBalance] = useState(10000);
  const [riskPercent, setRiskPercent] = useState(1.0);
  const [leverage, setLeverage] = useState(1.0);
  const [rrRatio, setRrRatio] = useState(2.0);

  // Live Position Evaluator variables
  const [trackedPositions, setTrackedPositions] = useState<Position[]>([
    {
      id: 1,
      symbol: "BTC/USDT",
      type: "long",
      strike: null,
      entry: 63000,
      limit: 66000,
      sl: 61500,
      timeframe: "1h"
    },
    {
      id: 2,
      symbol: "AAPL",
      type: "call",
      strike: 220,
      entry: 3.5,
      limit: 7.0,
      sl: 1.5,
      timeframe: "1h"
    }
  ]);

  // Dynamic dashboard states
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Positions evaluation results
  const [evaluationResults, setEvaluationResults] = useState<Record<number, any>>({});
  const [evaluatingAll, setEvaluatingAll] = useState(false);

  // Alerts Feed
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isScanning, setIsScanning] = useState(false);

  // Forms to add active positions
  const [formSymbol, setFormSymbol] = useState("");
  const [formType, setFormType] = useState<Position["type"]>("long");
  const [formStrike, setFormStrike] = useState("");
  const [formEntry, setFormEntry] = useState("");
  const [formLimit, setFormLimit] = useState("");
  const [formSl, setFormSl] = useState("");
  const [formTf, setFormTf] = useState("1h");

  // Options Chains ATM display
  const [chainData, setChainData] = useState<any>(null);
  const [loadingChain, setLoadingChain] = useState(false);

  // Backtest simulation metrics
  const [backtestMetrics, setBacktestMetrics] = useState<any>(null);
  const [runningBacktest, setRunningBacktest] = useState(false);

  // Sizing Calculator parameters
  const [calcEntry, setCalcEntry] = useState<number>(0);
  const [calcSL, setCalcSL] = useState<number>(0);
  const [calcResult, setCalcResult] = useState<any>(null);

  // Preset symbols
  const cryptoPresets = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "DOT/USDT"];
  const foPresets = ["^NSEI", "^NSEBANK", "AAPL", "SPY", "QQQ", "RELIANCE.NS"];

  // 1. Fetch live analysis for selected symbol
  const fetchAnalysis = async (symbol: string, tf: string) => {
    setIsLoading(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API_URL}/api/analyze?symbol=${encodeURIComponent(symbol)}&timeframe=${tf}`);
      if (!res.ok) throw new Error("Could not retrieve market analysis");
      const data = await res.json();
      setAnalysisData(data);
      if (data.current_price) {
        setCalcEntry(data.current_price);
        // Default SL: 2 ATR below entry for Buy
        const atr = data.indicators?.latest?.atr_14 || (data.current_price * 0.02);
        setCalcSL(data.current_price - 2 * atr);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load dashboard data");
    } finally {
      setIsLoading(false);
    }
  };

  // 2. Fetch Options chains metrics
  const fetchOptionsChain = async (symbol: string) => {
    setLoadingChain(true);
    setChainData(null);
    try {
      const res = await fetch(`${API_URL}/api/options-chain?symbol=${encodeURIComponent(symbol)}`);
      if (res.ok) {
        const data = await res.json();
        setChainData(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingChain(false);
    }
  };

  // 3. Scan Range Filter Signals
  const scanSignals = async () => {
    setIsScanning(true);
    try {
      const res = await fetch(`${API_URL}/api/signals-scan`);
      if (res.ok) {
        const data = await res.json();
        // Check for new signals
        const existing = new Set(alerts.map(a => `${a.symbol}_${a.signal}`));
        const newAlerts: Alert[] = [];
        data.forEach((alert: Alert) => {
          if (!existing.has(`${alert.symbol}_${alert.signal}`)) {
            newAlerts.push(alert);
            // Push browser notifications using browser Notification API if granted
            if (Notification.permission === "granted") {
              new Notification(`🔔 ${alert.symbol}: ${alert.signal}`, {
                body: `Range Filter crossover trigger @ $${alert.price.toLocaleString()}`,
                icon: "/favicon.ico"
              });
            }
          }
        });

        if (newAlerts.length > 0) {
          setAlerts(prev => [...newAlerts, ...prev].slice(0, 30));
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsScanning(false);
    }
  };

  // 4. Evaluate single tracked holding position
  const evaluatePosition = async (pos: Position) => {
    try {
      const res = await fetch(`${API_URL}/api/evaluate-position`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: pos.symbol,
          position_type: pos.type,
          entry_price: pos.entry,
          limit_price: pos.limit,
          stop_loss: pos.sl,
          strike: pos.strike,
          timeframe: pos.timeframe
        })
      });
      if (res.ok) {
        const data = await res.json();
        setEvaluationResults(prev => ({ ...prev, [pos.id]: data }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  // 5. Evaluate all holdings
  const evaluateAllPositions = async () => {
    setEvaluatingAll(true);
    await Promise.all(trackedPositions.map(pos => evaluatePosition(pos)));
    setEvaluatingAll(false);
  };

  // 6. Run backtester simulation
  const runBacktest = async () => {
    setRunningBacktest(true);
    setBacktestMetrics(null);
    try {
      const res = await fetch(`${API_URL}/api/backtest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: activeSymbol,
          timeframe: timeframe,
          risk_percent: riskPercent,
          leverage: leverage,
          risk_reward_ratio: rrRatio,
          initial_capital: balance
        })
      });
      if (res.ok) {
        const data = await res.json();
        setBacktestMetrics(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRunningBacktest(false);
    }
  };

  // 7. Calculate capital Sizing Planner
  const calculateSizing = () => {
    if (calcEntry <= 0 || calcSL <= 0 || calcEntry === calcSL) return;
    const isBuy = calcEntry > calcSL;
    const riskPerUnit = Math.abs(calcEntry - calcSL);
    const capitalAtRisk = balance * (riskPercent / 100);
    const rawUnits = capitalAtRisk / riskPerUnit;
    const units = rawUnits * leverage;
    const purchaseValue = units * calcEntry;
    const marginRequired = purchaseValue / leverage;

    setCalcResult({
      capitalAtRisk,
      units,
      purchaseValue,
      marginRequired,
      riskPerUnit
    });
  };

  // Request browser notification permissions on mount
  useEffect(() => {
    if (Notification.permission === "default") {
      Notification.requestPermission();
    }
    
    // Initial scan and sets timer
    scanSignals();
    const alertTimer = setInterval(scanSignals, 45000);
    return () => clearInterval(alertTimer);
  }, []);

  // Fetch when symbol/timeframe switches
  useEffect(() => {
    fetchAnalysis(activeSymbol, timeframe);
    const isCrypto = cryptoPresets.includes(activeSymbol);
    if (!isCrypto) {
      fetchOptionsChain(activeSymbol);
    } else {
      setChainData(null);
    }
  }, [activeSymbol, timeframe]);

  // Calculate sizing whenever inputs adjust
  useEffect(() => {
    calculateSizing();
  }, [calcEntry, calcSL, balance, riskPercent, leverage]);

  // Evaluate holdings on load or when size modifies
  useEffect(() => {
    if (trackedPositions.length > 0) {
      evaluateAllPositions();
    }
  }, [trackedPositions]);

  // Trigger preset select
  const handlePresetSelect = (sym: string) => {
    setActiveSymbol(sym);
    setCustomSymbol("");
  };

  // Custom search entry
  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customSymbol.trim()) {
      setActiveSymbol(customSymbol.trim().toUpperCase());
    }
  };

  // Add position handler
  const handleAddPosition = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formSymbol) return;

    const newPos: Position = {
      id: Date.now(),
      symbol: formSymbol.toUpperCase(),
      type: formType,
      strike: formStrike ? parseFloat(formStrike) : null,
      entry: parseFloat(formEntry) || 0,
      limit: parseFloat(formLimit) || 0,
      sl: parseFloat(formSl) || 0,
      timeframe: formTf
    };

    setTrackedPositions(prev => [...prev, newPos]);
    // reset form
    setFormSymbol("");
    setFormStrike("");
    setFormEntry("");
    setFormLimit("");
    setFormSl("");
  };

  // Remove position
  const handleRemovePosition = (id: number) => {
    setTrackedPositions(prev => prev.filter(p => p.id !== id));
    setEvaluationResults(prev => {
      const updated = { ...prev };
      delete updated[id];
      return updated;
    });
  };

  return (
    <div className="terminal-container">
      {/* 1. LEFT SIDEBAR PANEL */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="live-dot" />
          <h1 className="sidebar-title">HEDGE-QUANT TERMINAL</h1>
        </div>

        <div className="sidebar-scroll">
          {/* Preset Selectors */}
          <div className="form-group">
            <label>Asset Class</label>
            <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
              <button 
                className={`btn-secondary ${assetClass === "Crypto" ? "active" : ""}`}
                style={{ flex: 1, borderColor: assetClass === "Crypto" ? "#2962ff" : "#2a2e39" }}
                onClick={() => setAssetClass("Crypto")}
              >
                Crypto
              </button>
              <button 
                className={`btn-secondary ${assetClass === "FO" ? "active" : ""}`}
                style={{ flex: 1, borderColor: assetClass === "FO" ? "#2962ff" : "#2a2e39" }}
                onClick={() => setAssetClass("FO")}
              >
                Stocks/FO
              </button>
            </div>
          </div>

          <div className="form-group">
            <label>Preset Symbols</label>
            <select 
              className="form-select"
              value={activeSymbol}
              onChange={(e) => handlePresetSelect(e.target.value)}
            >
              {assetClass === "Crypto" 
                ? cryptoPresets.map(s => <option key={s} value={s}>{s}</option>)
                : foPresets.map(s => <option key={s} value={s}>{s}</option>)
              }
            </select>
          </div>

          <form className="form-group" onSubmit={handleCustomSubmit}>
            <label>Search Symbol</label>
            <div style={{ display: "flex", gap: "8px" }}>
              <input 
                type="text" 
                className="form-input" 
                placeholder="e.g. BTC/USDT, TSLA"
                value={customSymbol}
                onChange={(e) => setCustomSymbol(e.target.value)}
              />
              <button type="submit" className="btn-secondary">Go</button>
            </div>
          </form>

          <div className="form-group">
            <label>Timeframe</label>
            <select 
              className="form-select"
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
            >
              <option value="5m">5 Minutes</option>
              <option value="15m">15 Minutes</option>
              <option value="1h">1 Hour</option>
              <option value="4h">4 Hours</option>
              <option value="1d">1 Day</option>
            </select>
          </div>

          <hr style={{ border: "0", borderTop: "1px solid #2a2e39", margin: "16px 0" }} />

          {/* Sizing Parameters */}
          <h3 style={{ fontSize: "11px", color: "#787b86", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "12px" }}>
            Sizing Metrics Configuration
          </h3>
          
          <div className="form-group">
            <label>Balance ($)</label>
            <input 
              type="number" 
              className="form-input" 
              value={balance}
              onChange={(e) => setBalance(parseFloat(e.target.value) || 10000)}
            />
          </div>

          <div className="form-group">
            <label>Max Risk: {riskPercent}%</label>
            <input 
              type="range" 
              min="0.1" 
              max="5.0" 
              step="0.1" 
              value={riskPercent}
              style={{ width: "100%" }}
              onChange={(e) => setRiskPercent(parseFloat(e.target.value) || 1.0)}
            />
          </div>

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
            <label>Target R:R ratio</label>
            <input 
              type="number" 
              className="form-input" 
              value={rrRatio}
              onChange={(e) => setRrRatio(parseFloat(e.target.value) || 2.0)}
            />
          </div>

          <hr style={{ border: "0", borderTop: "1px solid #2a2e39", margin: "16px 0" }} />

          {/* Live Alerts feed */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "11px", color: "#787b86", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>
              🔔 Range Filter Alerts Feed
            </span>
            <button 
              className="btn-secondary" 
              style={{ padding: "2px 6px", fontSize: "10px", display: "flex", alignItems: "center", gap: "4px" }}
              onClick={scanSignals}
              disabled={isScanning}
            >
              <RefreshCw size={10} className={isScanning ? "spin" : ""} /> Scan
            </button>
          </div>

          <div style={{ maxHeight: "200px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "5px" }}>
            {alerts.length === 0 ? (
              <div style={{ color: "#787b86", fontSize: "11px", textAlign: "center", padding: "10px 0" }}>
                No active Range Filter triggers detected.
              </div>
            ) : (
              alerts.map((alert, idx) => (
                <div key={idx} className={`alert-item ${alert.signal.toLowerCase()}`}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <strong>{alert.symbol}</strong>
                    <span style={{ color: alert.signal === "BUY" ? "#089981" : "#f23645", fontWeight: "bold" }}>
                      {alert.signal}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "#787b86", fontSize: "10px", marginTop: "2px" }}>
                    <span>Price: ${alert.price.toLocaleString()}</span>
                    <span>{alert.timestamp}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* 2. MAIN APP FRAME */}
      <main className="main-workspace">
        <header className="workspace-header">
          <div className="workspace-header-title">
            Active: <span style={{ color: "#2962ff" }}>{activeSymbol}</span> ({timeframe}) | Live Streaming Feed
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button 
              className={`btn-secondary ${activeTab === "terminal" ? "active" : ""}`}
              onClick={() => setActiveTab("terminal")}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <TrendingUp size={14} /> Terminal
            </button>
            <button 
              className={`btn-secondary ${activeTab === "holdings" ? "active" : ""}`}
              onClick={() => setActiveTab("holdings")}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <Layers size={14} /> Holdings Tracker ({trackedPositions.length})
            </button>
          </div>
        </header>

        {activeTab === "terminal" ? (
          /* ==================================================== */
          /* TERMINAL TAB SCREEN                                  */
          /* ==================================================== */
          <div className="workspace-content">
            {isLoading ? (
              <div style={{ textAlign: "center", padding: "100px 0", color: "#787b86" }}>
                <RefreshCw className="spin" size={32} style={{ marginBottom: "10px" }} />
                <div>Fetching market structures, sentiment arrays, and ML models...</div>
              </div>
            ) : errorMsg ? (
              <div style={{ padding: "40px", backgroundColor: "rgba(242, 54, 69, 0.1)", borderRadius: "6px", border: "1px solid #f23645", color: "#f23645" }}>
                <strong>Error:</strong> {errorMsg}
                <button className="btn-primary" style={{ marginTop: "15px", width: "auto" }} onClick={() => fetchAnalysis(activeSymbol, timeframe)}>
                  Retry Request
                </button>
              </div>
            ) : analysisData ? (
              <div className="split-layout">
                {/* Left side: Interactive Candlestick charts */}
                <div className="split-left">
                  <div className="tv-panel" style={{ padding: "8px" }}>
                    <div className="tv-panel-header" style={{ padding: "8px 12px 0 12px", borderBottom: "none" }}>
                      <span>📈 PRICE CHART & RANGE FILTER OVERLAYS</span>
                      <span style={{ color: "#787b86", fontSize: "10px" }}>Websocket Connected</span>
                    </div>
                    {analysisData.chart_data && (
                      <TradingViewChart candles={analysisData.chart_data} symbol={activeSymbol} />
                    )}
                  </div>

                  {/* Sub Panel with analysis tools */}
                  <div className="tv-panel">
                    <div className="tv-panel-header">
                      <span>🧠 AI ANALYST RESEARCH LOG REPORT</span>
                      <span style={{ color: "#2962ff", display: "flex", alignItems: "center", gap: "4px" }}>
                        <Sparkles size={11} /> Calibrated Forecast
                      </span>
                    </div>
                    <div className="report-markdown" dangerouslySetInnerHTML={{ __html: analysisData.report?.replace(/\n/g, "<br/>") || "" }} />
                  </div>
                </div>

                {/* Right side: TradingView style scorecards & gauge dial */}
                <div className="split-right">
                  {/* Gauge indicator widget */}
                  <div className="tv-panel" style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div className="tv-panel-header" style={{ width: "100%" }}>
                      <span>🎯 Technical Consensus Speedometer</span>
                    </div>
                    {(() => {
                      const latest = analysisData.indicators?.latest || {};
                      const sig = analysisData.prediction?.signal || "HOLD";
                      const pcr = chainData?.pcr_oi || 1.0;
                      const rsi = latest.rsi_14 || 50;
                      const score = analysisData.sentiment?.score || 0;

                      // Gauge Rating Calculation
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

                      if (rating >= 70) { conLabel = "STRONG BUY"; conColor = "#089981"; }
                      else if (rating >= 55) { conLabel = "BUY"; conColor = "#26a69a"; }
                      else if (rating <= 30) { conLabel = "STRONG SELL"; conColor = "#f23645"; }
                      else if (rating <= 45) { conLabel = "SELL"; conColor = "#ff5252"; }

                      return (
                        <ConsensusGauge value={rating} label={conLabel} color={conColor} />
                      );
                    })()}
                  </div>

                  {/* Core specs scorecards */}
                  <div className="tv-panel">
                    <div className="tv-panel-header">
                      <span>📊 Asset Scorecards</span>
                    </div>
                    <div className="tv-scorecard">
                      <div className="tv-scorecard-label">Last Traded price</div>
                      <div className="tv-scorecard-value">
                        ${analysisData.current_price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                      </div>
                      <div className="tv-scorecard-sub">Active Feed Price</div>
                    </div>

                    <div className="tv-scorecard">
                      <div className="tv-scorecard-label">AI Forecast (ML Calibrated)</div>
                      <div style={{ marginTop: "4px" }}>
                        <span className={analysisData.prediction?.signal === "BUY" ? "badge-buy" : analysisData.prediction?.signal === "SELL" ? "badge-sell" : "badge-hold"}>
                          {analysisData.prediction?.signal || "HOLD"} ({((analysisData.prediction?.confidence || 0.5) * 100).toFixed(0)}% Conv)
                        </span>
                      </div>
                      <div className="tv-scorecard-sub">Next-period direction skew</div>
                    </div>

                    <div className="tv-scorecard">
                      <div className="tv-scorecard-label">Overall sentiment</div>
                      <div style={{ marginTop: "4px" }}>
                        <span className={analysisData.sentiment?.label === "bullish" ? "badge-buy" : analysisData.sentiment?.label === "bearish" ? "badge-sell" : "badge-hold"}>
                          {analysisData.sentiment?.label?.toUpperCase() || "NEUTRAL"} ({analysisData.sentiment?.score})
                        </span>
                      </div>
                      <div className="tv-scorecard-sub">News & forums aggregated sentiment</div>
                    </div>
                  </div>

                  {/* Sizing calculation scorecard */}
                  <div className="tv-panel">
                    <div className="tv-panel-header">
                      <span>🧮 Capital Sizing Planner</span>
                    </div>
                    
                    <div className="form-group">
                      <label>Trade Entry price ($)</label>
                      <input 
                        type="number" 
                        className="form-input" 
                        value={calcEntry}
                        onChange={(e) => setCalcEntry(parseFloat(e.target.value) || 0)}
                      />
                    </div>

                    <div className="form-group">
                      <label>Trade Stop Loss ($)</label>
                      <input 
                        type="number" 
                        className="form-input" 
                        value={calcSL}
                        onChange={(e) => setCalcSL(parseFloat(e.target.value) || 0)}
                      />
                    </div>

                    {calcResult && (
                      <div style={{ marginTop: "12px", borderTop: "1px solid #2a2e39", paddingTop: "12px", display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px" }}>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Risk per Unit:</span>
                          <strong>${calcResult.riskPerUnit.toFixed(2)}</strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Total cash at Risk:</span>
                          <strong style={{ color: "#f23645" }}>${calcResult.capitalAtRisk.toFixed(2)}</strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Calculated Units:</span>
                          <strong>{calcResult.units.toFixed(4)}</strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Margin required:</span>
                          <strong style={{ color: "#089981" }}>${calcResult.marginRequired.toFixed(2)}</strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Purchase value:</span>
                          <strong>${calcResult.purchaseValue.toFixed(2)}</strong>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Options derivatives info if present */}
                  {!cryptoPresets.includes(activeSymbol) && chainData && (
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

                  {/* Backtest Strategy Simulator */}
                  <div className="tv-panel">
                    <div className="tv-panel-header">
                      <span>🔄 Strategy Backtester Simulator</span>
                    </div>
                    <button 
                      className="btn-primary" 
                      onClick={runBacktest}
                      disabled={runningBacktest}
                      style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
                    >
                      <Play size={13} fill="white" /> {runningBacktest ? "Simulating Strategy..." : "Run SMC Backtest"}
                    </button>

                    {backtestMetrics && (
                      <div style={{ marginTop: "12px", borderTop: "1px solid #2a2e39", paddingTop: "12px", display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px" }}>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Win Rate:</span>
                          <strong style={{ color: "#089981" }}>{backtestMetrics.metrics?.win_rate_pct}%</strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Net Return:</span>
                          <strong style={{ color: backtestMetrics.metrics?.total_return_pct >= 0 ? "#089981" : "#f23645" }}>
                            {backtestMetrics.metrics?.total_return_pct >= 0 ? "+" : ""}{backtestMetrics.metrics?.total_return_pct}%
                          </strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Profit Factor:</span>
                          <strong>{backtestMetrics.metrics?.profit_factor}</strong>
                        </div>
                        <div className="p-flex-between">
                          <span style={{ color: "#787b86" }}>Max Drawdown:</span>
                          <strong style={{ color: "#f23645" }}>{backtestMetrics.metrics?.max_drawdown_pct}%</strong>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: "center", padding: "100px 0", color: "#787b86" }}>
                Select preset symbol on the left to pull live metrics.
              </div>
            )}
          </div>
        ) : (
          /* ==================================================== */
          /* ACTIVE HOLDINGS TRACKER TAB                          */
          /* ==================================================== */
          <div className="workspace-content">
            <div className="split-layout">
              {/* Left Side: Tracked positions cards list */}
              <div className="split-left">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <h3 style={{ margin: 0, color: "#f0f3fa", fontSize: "16px" }}>Tracked Holdings Portfolio</h3>
                  <button className="btn-secondary" onClick={evaluateAllPositions} disabled={evaluatingAll}>
                    <RefreshCw size={12} className={evaluatingAll ? "spin" : ""} style={{ marginRight: "6px" }} />
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
                        <div key={pos.id} className="tv-panel" style={{ position: "relative" }}>
                          {/* Glowing Advice Banner */}
                          {evalRes ? (
                            advice === "Keep it" ? (
                              <div className="glowing-card-keep">
                                <h4 style={{ margin: 0, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px" }}>
                                  <CheckCircle2 size={16} /> DIRECTIVE: KEEP IT (📈 Predict Rise / Continuation)
                                </h4>
                              </div>
                            ) : (
                              <div className="glowing-card-sell">
                                <h4 style={{ margin: 0, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px" }}>
                                  <ShieldAlert size={16} /> DIRECTIVE: SELL IT (📉 Predict Drop / Risk Exit)
                                </h4>
                              </div>
                            )
                          ) : (
                            <div style={{ backgroundColor: "#1c2030", padding: "12px", borderRadius: "6px", color: "#787b86", marginBottom: "12px", fontSize: "12px" }}>
                              Evaluating active pricing...
                            </div>
                          )}

                          <div className="p-flex-between" style={{ borderBottom: "1px solid #2a2e39", paddingBottom: "10px", marginBottom: "12px" }}>
                            <div>
                              <span style={{ fontSize: "16px", fontWeight: 700, color: "#f0f3fa", marginRight: "8px" }}>
                                {pos.symbol}
                              </span>
                              <span className={pos.type === "long" || pos.type === "call" ? "badge-buy" : "badge-sell"}>
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
                              style={{ color: "#f23645", borderColor: "rgba(242, 54, 69, 0.2)", display: "flex", alignItems: "center", padding: "4px 8px" }}
                              onClick={() => handleRemovePosition(pos.id)}
                            >
                              <Trash2 size={12} style={{ marginRight: "4px" }} /> Delete
                            </button>
                          </div>

                          <div className="p-grid-2">
                            {/* Position Details */}
                            <div style={{ fontSize: "13px", display: "flex", flexDirection: "column", gap: "6px" }}>
                              <div className="p-flex-between">
                                <span style={{ color: "#787b86" }}>Entry price:</span>
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

                            {/* Position Evaluation outputs */}
                            {evalRes && (
                              <div style={{ fontSize: "13px", display: "flex", flexDirection: "column", gap: "6px", borderLeft: "1px solid #2a2e39", paddingLeft: "16px" }}>
                                <div className="p-flex-between">
                                  <span style={{ color: "#787b86" }}>Current Spot:</span>
                                  <strong>${evalRes.spot_price?.toLocaleString()}</strong>
                                </div>
                                <div className="p-flex-between">
                                  <span style={{ color: "#787b86" }}>PnL Net:</span>
                                  <strong style={{ color: evalRes.pnl_percentage >= 0 ? "#089981" : "#f23645" }}>
                                    {evalRes.pnl_percentage >= 0 ? "+" : ""}{evalRes.pnl_percentage}%
                                  </strong>
                                </div>
                                <div className="p-flex-between">
                                  <span style={{ color: "#787b86" }}>ML Alignment:</span>
                                  <strong>{evalRes.ml_aligned ? "Aligned 🟢" : "Conflict ⚠️"}</strong>
                                </div>
                                <div className="p-flex-between" style={{ flexDirection: "column", alignItems: "flex-start", gap: "4px" }}>
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

              {/* Right Side: Track new holding registration form */}
              <div className="split-right">
                <div className="tv-panel">
                  <div className="tv-panel-header">
                    <span>➕ Track New Position</span>
                  </div>

                  <form onSubmit={handleAddPosition} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <div className="form-group">
                      <label>Asset Symbol</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        required 
                        placeholder="e.g. BTC/USDT, TSLA"
                        value={formSymbol}
                        onChange={(e) => setFormSymbol(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label>Position type</label>
                      <select 
                        className="form-select"
                        value={formType}
                        onChange={(e) => setFormType(e.target.value as Position["type"])}
                      >
                        <option value="long">Long</option>
                        <option value="short">Short</option>
                        <option value="call">Call Option</option>
                        <option value="put">Put Option</option>
                      </select>
                    </div>

                    {(formType === "call" || formType === "put") && (
                      <div className="form-group">
                        <label>Strike price ($)</label>
                        <input 
                          type="number" 
                          className="form-input" 
                          placeholder="e.g. 220"
                          value={formStrike}
                          onChange={(e) => setFormStrike(e.target.value)}
                        />
                      </div>
                    )}

                    <div className="form-group">
                      <label>Entry price ($)</label>
                      <input 
                        type="number" 
                        step="0.0001" 
                        className="form-input" 
                        required
                        placeholder="e.g. 63000"
                        value={formEntry}
                        onChange={(e) => setFormEntry(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label>Exit Limit Target ($)</label>
                      <input 
                        type="number" 
                        step="0.0001" 
                        className="form-input" 
                        required
                        placeholder="e.g. 66000"
                        value={formLimit}
                        onChange={(e) => setFormLimit(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label>Stop Loss ($)</label>
                      <input 
                        type="number" 
                        step="0.0001" 
                        className="form-input" 
                        required
                        placeholder="e.g. 61500"
                        value={formSl}
                        onChange={(e) => setFormSl(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label>Scan Timeframe</label>
                      <select 
                        className="form-select"
                        value={formTf}
                        onChange={(e) => setFormTf(e.target.value)}
                      >
                        <option value="5m">5m</option>
                        <option value="15m">15m</option>
                        <option value="1h">1h</option>
                        <option value="4h">4h</option>
                        <option value="1d">1d</option>
                      </select>
                    </div>

                    <button type="submit" className="btn-primary" style={{ marginTop: "10px" }}>
                      Add Position to Tracker
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

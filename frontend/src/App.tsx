import React, { useState, useEffect } from "react";
import { TrendingUp, Layers, RefreshCw, Activity, Sparkles, Newspaper, Bot } from "lucide-react";
import { TerminalTab } from "./components/TerminalTab";
import { AllIndicatorsHub } from "./components/AllIndicatorsHub";
import { AICopilotTab } from "./components/AICopilotTab";
import { NewsSentimentTab } from "./components/NewsSentimentTab";
import { HoldingsTab } from "./components/HoldingsTab";
import { AddPositionForm } from "./components/AddPositionForm";
import { DeltaAutoTraderTab } from "./components/DeltaAutoTraderTab";

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

interface TickerItem {
  symbol: string;
  price: number;
  change_pct: number;
  high: number;
  low: number;
  volume: number;
}

const API_URL = "http://localhost:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState<"terminal" | "indicators" | "copilot" | "news" | "holdings" | "delta">("terminal");
  const [assetClass, setAssetClass] = useState<"Crypto" | "FO">("Crypto");
  const [activeSymbol, setActiveSymbol] = useState("BTC/USDT");
  const [customSymbol, setCustomSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("1h");

  // Top Marquee Ticker
  const [tickerItems, setTickerItems] = useState<TickerItem[]>([]);

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
      entry: 64200,
      limit: 67500,
      sl: 62800,
      timeframe: "1h"
    },
    {
      id: 2,
      symbol: "ETH/USDT",
      type: "long",
      strike: null,
      entry: 2650,
      limit: 2850,
      sl: 2540,
      timeframe: "1h"
    },
    {
      id: 3,
      symbol: "XAUT/USDT",
      type: "long",
      strike: null,
      entry: 2510,
      limit: 2600,
      sl: 2470,
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

  // Backtest simulation metrics
  const [backtestMetrics, setBacktestMetrics] = useState<any>(null);
  const [runningBacktest, setRunningBacktest] = useState(false);

  // Sizing Calculator parameters
  const [calcEntry, setCalcEntry] = useState<number>(0);
  const [calcSL, setCalcSL] = useState<number>(0);
  const [calcResult, setCalcResult] = useState<any>(null);

  // Preset symbols - Showcase BTC, ETH, XAUT
  const cryptoPresets = ["BTC/USDT", "ETH/USDT", "XAUT/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT", "ADA/USDT", "DOGE/USDT"];
  const foPresets = ["^NSEI", "^NSEBANK", "AAPL", "SPY", "QQQ", "NVDA", "TSLA", "RELIANCE.NS"];

  // 1. Fetch Marquee Ticker overview
  const fetchMarketOverview = async () => {
    try {
      const res = await fetch(`${API_URL}/api/market-overview`);
      if (res.ok) {
        const data = await res.json();
        setTickerItems(data);
      }
    } catch (err) {
      console.error("Failed to fetch market overview:", err);
    }
  };

  // 2. Fetch live analysis for selected symbol
  const fetchAnalysis = async (symbol: string, tf: string) => {
    setIsLoading(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API_URL}/api/analyze?symbol=${encodeURIComponent(symbol)}&timeframe=${tf}`);
      if (!res.ok) throw new Error(`Could not retrieve market analysis for ${symbol}`);
      const data = await res.json();
      setAnalysisData(data);
      if (data.current_price) {
        setCalcEntry(data.current_price);
        const atr = data.indicators?.latest?.atr_14 || (data.current_price * 0.02);
        setCalcSL(data.current_price - 2 * atr);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load dashboard data");
    } finally {
      setIsLoading(false);
    }
  };

  // 3. Fetch Options chains metrics
  const fetchOptionsChain = async (symbol: string) => {
    setChainData(null);
    try {
      const res = await fetch(`${API_URL}/api/options-chain?symbol=${encodeURIComponent(symbol)}`);
      if (res.ok) {
        const data = await res.json();
        setChainData(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // 4. Scan Range Filter Signals
  const scanSignals = async () => {
    setIsScanning(true);
    try {
      const res = await fetch(`${API_URL}/api/signals-scan`);
      if (res.ok) {
        const data = await res.json();
        const existing = new Set(alerts.map(a => `${a.symbol}_${a.signal}`));
        const newAlerts: Alert[] = [];
        data.forEach((alert: Alert) => {
          if (!existing.has(`${alert.symbol}_${alert.signal}`)) {
            newAlerts.push(alert);
            if (Notification.permission === "granted") {
              new Notification(`🔔 ${alert.symbol}: ${alert.signal}`, {
                body: `Range Filter trigger @ $${alert.price.toLocaleString()}`,
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

  // 5. Evaluate single tracked holding position
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

  // 6. Evaluate all holdings
  const evaluateAllPositions = async () => {
    setEvaluatingAll(true);
    await Promise.all(trackedPositions.map(pos => evaluatePosition(pos)));
    setEvaluatingAll(false);
  };

  // 7. Run backtester simulation
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

  // 8. Calculate capital Sizing Planner
  const calculateSizing = () => {
    if (calcEntry <= 0 || calcSL <= 0 || calcEntry === calcSL) return;
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

  useEffect(() => {
    if (Notification.permission === "default") {
      Notification.requestPermission();
    }
    fetchMarketOverview();
    scanSignals();
    const overviewTimer = setInterval(fetchMarketOverview, 15000);
    const alertTimer = setInterval(scanSignals, 45000);
    return () => {
      clearInterval(overviewTimer);
      clearInterval(alertTimer);
    };
  }, []);

  useEffect(() => {
    fetchAnalysis(activeSymbol, timeframe);
    const isCrypto = cryptoPresets.includes(activeSymbol) || activeSymbol.includes("/");
    if (!isCrypto) {
      fetchOptionsChain(activeSymbol);
    } else {
      setChainData(null);
    }
  }, [activeSymbol, timeframe]);

  useEffect(() => {
    calculateSizing();
  }, [calcEntry, calcSL, balance, riskPercent, leverage]);

  useEffect(() => {
    if (trackedPositions.length > 0) {
      evaluateAllPositions();
    }
  }, [trackedPositions]);

  const handlePresetSelect = (sym: string) => {
    setActiveSymbol(sym);
    setCustomSymbol("");
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customSymbol.trim()) {
      setActiveSymbol(customSymbol.trim().toUpperCase());
    }
  };

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
    setFormSymbol("");
    setFormStrike("");
    setFormEntry("");
    setFormLimit("");
    setFormSl("");
  };

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
          <h1 className="sidebar-title">QUANT TERMINAL</h1>
        </div>

        <div className="sidebar-scroll">
          {/* Quick Token Showcase: BTC, ETH, XAUT */}
          <div className="form-group">
            <label>⚡ Quick Crypto & Gold Chips</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "6px", marginBottom: "8px" }}>
              {["BTC/USDT", "ETH/USDT", "XAUT/USDT"].map((s) => (
                <button
                  key={s}
                  className={`btn-secondary ${activeSymbol === s ? "active" : ""}`}
                  style={{
                    borderColor: activeSymbol === s ? "#2962ff" : "#2a2e39",
                    backgroundColor: activeSymbol === s ? "rgba(41, 98, 255, 0.2)" : "transparent",
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "6px 2px",
                    color: activeSymbol === s ? "#2962ff" : "#d1d4dc"
                  }}
                  onClick={() => handlePresetSelect(s)}
                >
                  {s.split("/")[0]}
                </button>
              ))}
            </div>
          </div>

          {/* Asset Class Selector */}
          <div className="form-group">
            <label>Asset Class</label>
            <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
              <button 
                className={`btn-secondary ${assetClass === "Crypto" ? "active" : ""}`}
                style={{ flex: 1, borderColor: assetClass === "Crypto" ? "#2962ff" : "#2a2e39" }}
                onClick={() => setAssetClass("Crypto")}
              >
                Crypto & Tokens
              </button>
              <button 
                className={`btn-secondary ${assetClass === "FO" ? "active" : ""}`}
                style={{ flex: 1, borderColor: assetClass === "FO" ? "#2962ff" : "#2a2e39" }}
                onClick={() => setAssetClass("FO")}
              >
                Stocks / Equities
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
            <label>Search Custom Symbol</label>
            <div style={{ display: "flex", gap: "8px" }}>
              <input 
                type="text" 
                className="form-input" 
                placeholder="e.g. BTC/USDT, XAUT/USDT, AAPL"
                value={customSymbol}
                onChange={(e) => setCustomSymbol(e.target.value)}
              />
              <button type="submit" className="btn-secondary">Go</button>
            </div>
          </form>

          <div className="form-group">
            <label>Timeframe Resolution</label>
            <select 
              className="form-select"
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
            >
              <option value="5m">5 Minutes (Scalp)</option>
              <option value="15m">15 Minutes (Intraday)</option>
              <option value="1h">1 Hour (Standard)</option>
              <option value="4h">4 Hours (Swing)</option>
              <option value="1d">1 Day (Macro Trend)</option>
            </select>
          </div>

          <hr style={{ border: "0", borderTop: "1px solid #2a2e39", margin: "16px 0" }} />

          {/* Live Alerts feed */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <span style={{ fontSize: "11px", color: "#787b86", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>
              🔔 Range Filter Triggers
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

          <div style={{ maxHeight: "250px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "5px" }}>
            {alerts.length === 0 ? (
              <div style={{ color: "#787b86", fontSize: "11px", textAlign: "center", padding: "10px 0" }}>
                Scanning real-time Range Filter triggers across assets...
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
        {/* TOP MARQUEE TICKER BAR */}
        <div className="marquee-container">
          <span style={{ fontSize: "11px", fontWeight: 700, color: "#2962ff", display: "flex", alignItems: "center", gap: "4px" }}>
            ⚡ LIVE TICKERS:
          </span>
          {tickerItems.length > 0 ? (
            tickerItems.map((t) => {
              const isPositive = t.change_pct >= 0;
              return (
                <div
                  key={t.symbol}
                  className={`marquee-item ${activeSymbol === t.symbol ? "active" : ""}`}
                  onClick={() => handlePresetSelect(t.symbol)}
                >
                  <strong style={{ color: "#fff" }}>{t.symbol}</strong>
                  <span style={{ fontFamily: "monospace" }}>${t.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}</span>
                  <span style={{ color: isPositive ? "#089981" : "#f23645", fontWeight: "bold", fontSize: "11px" }}>
                    {isPositive ? "+" : ""}{t.change_pct}%
                  </span>
                </div>
              );
            })
          ) : (
            <div style={{ fontSize: "11px", color: "#787b86" }}>Loading live prices for BTC, ETH, XAUT, SOL, XRP...</div>
          )}
        </div>

        {/* WORKSPACE HEADER WITH NAVIGATION TABS */}
        <header className="workspace-header">
          <div className="workspace-header-title">
            Asset: <span style={{ color: "#2962ff", fontWeight: 700 }}>{activeSymbol}</span> ({timeframe}) | Spot: <strong style={{ color: "#00E676" }}>${analysisData?.current_price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 }) || "..."}</strong>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <button 
              className={`btn-secondary ${activeTab === "terminal" ? "active" : ""}`}
              onClick={() => setActiveTab("terminal")}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <TrendingUp size={14} /> Terminal
            </button>

            <button 
              className={`btn-secondary ${activeTab === "indicators" ? "active" : ""}`}
              onClick={() => setActiveTab("indicators")}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <Activity size={14} /> All Indicators Hub
            </button>

            <button 
              className={`btn-secondary ${activeTab === "copilot" ? "active" : ""}`}
              onClick={() => setActiveTab("copilot")}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <Sparkles size={14} /> AI Copilot & Dossier
            </button>

            <button 
              className={`btn-secondary ${activeTab === "news" ? "active" : ""}`}
              onClick={() => setActiveTab("news")}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <Newspaper size={14} /> News & Sentiment
            </button>

            <button 
              className={`btn-secondary ${activeTab === "delta" ? "active" : ""}`}
              onClick={() => setActiveTab("delta")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                borderColor: activeTab === "delta" ? "#089981" : "#2a2e39",
                color: activeTab === "delta" ? "#089981" : "#d1d4dc",
                fontWeight: 600
              }}
            >
              <Bot size={14} style={{ color: "#089981" }} /> Delta Auto-Trader ⚡
            </button>

            <button 
              className={`btn-secondary ${activeTab === "holdings" ? "active" : ""}`}
              onClick={() => setActiveTab("holdings")}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <Layers size={14} /> Holdings ({trackedPositions.length})
            </button>
          </div>
        </header>

        {/* WORKSPACE TAB CONTENT ROUTER */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
          {activeTab === "terminal" && (
            <TerminalTab
              isLoading={isLoading}
              errorMsg={errorMsg}
              analysisData={analysisData}
              activeSymbol={activeSymbol}
              timeframe={timeframe}
              fetchAnalysis={fetchAnalysis}
              cryptoPresets={cryptoPresets}
              chainData={chainData}
              backtestMetrics={backtestMetrics}
              runningBacktest={runningBacktest}
              runBacktest={runBacktest}
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
          )}

          {activeTab === "indicators" && (
            <AllIndicatorsHub
              analysisData={analysisData}
              activeSymbol={activeSymbol}
            />
          )}

          {activeTab === "copilot" && (
            <AICopilotTab
              analysisData={analysisData}
              activeSymbol={activeSymbol}
            />
          )}

          {activeTab === "news" && (
            <NewsSentimentTab
              sentimentData={analysisData?.sentiment}
              activeSymbol={activeSymbol}
              onRefresh={() => fetchAnalysis(activeSymbol, timeframe)}
              isLoading={isLoading}
            />
          )}

          {activeTab === "delta" && (
            <DeltaAutoTraderTab
              activeSymbol={activeSymbol}
            />
          )}

          {activeTab === "holdings" && (
            <HoldingsTab
              trackedPositions={trackedPositions}
              evaluationResults={evaluationResults}
              evaluatingAll={evaluatingAll}
              evaluateAllPositions={evaluateAllPositions}
              handleRemovePosition={handleRemovePosition}
              addPositionForm={
                <AddPositionForm
                  formSymbol={formSymbol}
                  setFormSymbol={setFormSymbol}
                  formType={formType}
                  setFormType={setFormType}
                  formStrike={formStrike}
                  setFormStrike={setFormStrike}
                  formEntry={formEntry}
                  setFormEntry={setFormEntry}
                  formLimit={formLimit}
                  setFormLimit={setFormLimit}
                  formSl={formSl}
                  setFormSl={setFormSl}
                  formTf={formTf}
                  setFormTf={setFormTf}
                  onSubmit={handleAddPosition}
                />
              }
            />
          )}
        </div>
      </main>
    </div>
  );
}

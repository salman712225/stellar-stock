import React, { useState, useEffect } from "react";
import { TrendingUp, Layers, RefreshCw } from "lucide-react";
import { TerminalTab } from "./components/TerminalTab";
import { HoldingsTab } from "./components/HoldingsTab";
import { AddPositionForm } from "./components/AddPositionForm";

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

  // 3. Scan Range Filter Signals
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

          <div style={{ maxHeight: "250px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "5px" }}>
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
        ) : (
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
      </main>
    </div>
  );
}

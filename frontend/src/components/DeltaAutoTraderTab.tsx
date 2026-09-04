import React, { useState, useEffect } from "react";
import { Bot, Power, ShieldAlert, Key, Zap, CheckCircle2, XCircle, RefreshCw, Play, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { API_URL } from "../config";

interface DeltaAutoTraderTabProps {
  activeSymbol: string;
}

export const DeltaAutoTraderTab: React.FC<DeltaAutoTraderTabProps> = ({ activeSymbol }) => {
  // Config state with localStorage fallbacks
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("stellar_delta_api_key") || "");
  const [apiSecret, setApiSecret] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [environment, setEnvironment] = useState<"testnet" | "global" | "india">(() => {
    return (localStorage.getItem("stellar_delta_environment") as any) || "testnet";
  });
  const [asset, setAsset] = useState(() => localStorage.getItem("stellar_default_asset") || activeSymbol || "BTC/USDT");
  const [timeframe, setTimeframe] = useState(() => localStorage.getItem("stellar_default_tf") || "1h");
  const [instrumentType, setInstrumentType] = useState<"options" | "futures">(() => {
    return (localStorage.getItem("stellar_default_instrument") as any) || "options";
  });
  const [sizeContracts, setSizeContracts] = useState(() => {
    const s = localStorage.getItem("stellar_default_size");
    return s ? parseInt(s) : 1;
  });
  const [strikeOffset, setStrikeOffset] = useState(() => {
    const s = localStorage.getItem("stellar_default_strike_offset");
    return s !== null ? parseInt(s) : 0;
  });
  const [stopLossPct, setStopLossPct] = useState(() => {
    const s = localStorage.getItem("stellar_default_sl");
    return s ? parseFloat(s) : 50;
  });
  const [isEnabled, setIsEnabled] = useState(false);

  // Status & Positions state
  const [connStatus, setConnStatus] = useState<any>(null);
  const [botStatus, setBotStatus] = useState<any>(null);
  const [positions, setPositions] = useState<any[]>([]);
  const [balances, setBalances] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Fetch status & logs
  const fetchStatusAndLogs = async () => {
    try {
      const [resStatus, resPos, resBal, resLogs] = await Promise.all([
        fetch(`${API_URL}/api/delta/status`),
        fetch(`${API_URL}/api/delta/positions`),
        fetch(`${API_URL}/api/delta/balances`),
        fetch(`${API_URL}/api/delta/logs`)
      ]);

      if (resStatus.ok) {
        const data = await resStatus.json();
        setConnStatus(data.connection);
        setBotStatus(data.bot);
        if (data.bot) {
          setIsEnabled(data.bot.enabled);
          setEnvironment(data.bot.environment || "testnet");
          setAsset(data.bot.asset || "BTC/USDT");
          setTimeframe(data.bot.timeframe || "1h");
          setInstrumentType(data.bot.instrument_type || "options");
          setSizeContracts(data.bot.size_contracts || 1);
          setStrikeOffset(data.bot.strike_offset || 0);
          setStopLossPct(data.bot.stop_loss_pct || 50);
        }
      }

      if (resPos.ok) {
        const pData = await resPos.json();
        setPositions(pData.positions || []);
      }

      if (resBal.ok) {
        const bData = await resBal.json();
        setBalances(bData.balances || []);
      }

      if (resLogs.ok) {
        const lData = await resLogs.json();
        setLogs(lData.logs || []);
      }
    } catch (err) {
      console.error("Error fetching Delta status:", err);
    }
  };

  useEffect(() => {
    fetchStatusAndLogs();
    const interval = setInterval(fetchStatusAndLogs, 4000);
    return () => clearInterval(interval);
  }, []);

  // Save Config & Credentials
  const handleSaveConfig = async (newEnabledState?: boolean) => {
    setIsLoading(true);
    try {
      const payload: any = {
        environment,
        asset,
        timeframe,
        instrument_type: instrumentType,
        size_contracts: sizeContracts,
        strike_offset: strikeOffset,
        stop_loss_pct: stopLossPct,
        enabled: newEnabledState !== undefined ? newEnabledState : isEnabled
      };

      if (apiKey.trim()) payload.api_key = apiKey.trim();
      if (apiSecret.trim()) payload.api_secret = apiSecret.trim();

      const res = await fetch(`${API_URL}/api/delta/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        await fetchStatusAndLogs();
      }
    } catch (err) {
      console.error("Failed to update Delta config:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle Auto-Trader Master Switch
  const toggleAutoTrader = async () => {
    const nextState = !isEnabled;
    setIsEnabled(nextState);
    await handleSaveConfig(nextState);
  };

  // Manual Trigger (BUY / SELL / CLOSE)
  const handleManualOrder = async (side: "BUY" | "SELL" | "CLOSE") => {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/delta/manual-order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side })
      });
      if (res.ok) {
        await fetchStatusAndLogs();
      }
    } catch (err) {
      console.error("Manual order failed:", err);
    } finally {
      setActionLoading(false);
    }
  };

  // Panic Kill Switch
  const handlePanicClose = async () => {
    if (!window.confirm("🚨 EMERGENCY ACTION: Are you sure you want to CLOSE ALL open positions immediately and STOP the Auto-Trader?")) {
      return;
    }
    setActionLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/delta/close-all`, {
        method: "POST"
      });
      if (res.ok) {
        setIsEnabled(false);
        await fetchStatusAndLogs();
      }
    } catch (err) {
      console.error("Panic close failed:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const activePos = botStatus?.active_position;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Top Banner: Status & Master Switch */}
      <div
        className="tv-panel"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
          background: isEnabled 
            ? "linear-gradient(135deg, rgba(8, 153, 129, 0.15) 0%, rgba(19, 23, 34, 0.95) 100%)" 
            : "linear-gradient(135deg, rgba(255, 152, 0, 0.1) 0%, rgba(19, 23, 34, 0.95) 100%)",
          borderColor: isEnabled ? "#089981" : "#2a2e39"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "10px",
              backgroundColor: isEnabled ? "#089981" : "#1e222d",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: isEnabled ? "0 0 16px rgba(8, 153, 129, 0.4)" : "none"
            }}
          >
            <Bot size={26} color="#fff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h2 style={{ margin: 0, fontSize: "18px", color: "#f0f3fa" }}>Delta Exchange Auto-Trader</h2>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: "4px",
                  backgroundColor: environment === "testnet" ? "rgba(255, 152, 0, 0.2)" : "rgba(8, 153, 129, 0.2)",
                  color: environment === "testnet" ? "#FF9800" : "#089981",
                  border: `1px solid ${environment === "testnet" ? "#FF9800" : "#089981"}`
                }}
              >
                {environment.toUpperCase()} {environment === "testnet" ? "SANDBOX" : "LIVE"}
              </span>
            </div>
            <div style={{ fontSize: "12px", color: "#787b86", marginTop: "4px" }}>
              Automated Options Execution on <strong>Range Filter Buy/Sell</strong> Signals
            </div>
          </div>
        </div>

        {/* Master ON/OFF Switch */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            onClick={toggleAutoTrader}
            disabled={isLoading || actionLoading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 20px",
              borderRadius: "6px",
              fontWeight: 700,
              fontSize: "14px",
              cursor: "pointer",
              border: "none",
              backgroundColor: isEnabled ? "#089981" : "#2a2e39",
              color: "#fff",
              boxShadow: isEnabled ? "0 0 20px rgba(8, 153, 129, 0.5)" : "none",
              transition: "all 0.2s ease"
            }}
          >
            {isEnabled ? <Power size={18} /> : <Play size={18} />}
            {isEnabled ? "AUTO-TRADER ACTIVE" : "PAUSED (START BOT)"}
          </button>

          <button
            className="btn-secondary"
            onClick={handlePanicClose}
            disabled={actionLoading}
            style={{
              backgroundColor: "rgba(242, 54, 69, 0.15)",
              borderColor: "#f23645",
              color: "#f23645",
              fontWeight: 700,
              padding: "10px 14px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "12px"
            }}
          >
            <ShieldAlert size={16} /> PANIC CLOSE ALL
          </button>
        </div>
      </div>

      {/* Active Position Hero Card */}
      {activePos ? (
        <div
          className="tv-panel"
          style={{
            borderColor: activePos.type === "call" ? "#089981" : "#f23645",
            background: activePos.type === "call" ? "rgba(8, 153, 129, 0.1)" : "rgba(242, 54, 69, 0.1)"
          }}
        >
          <div className="tv-panel-header">
            <span style={{ color: activePos.type === "call" ? "#089981" : "#f23645", display: "flex", alignItems: "center", gap: "6px" }}>
              {activePos.type === "call" ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
              ACTIVE POSITION: <strong>{activePos.symbol}</strong> ({activePos.type?.toUpperCase()})
            </span>
            <span style={{ color: "#787b86", fontSize: "11px" }}>Opened at {activePos.opened_at}</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px", fontSize: "12px" }}>
            <div>
              <div style={{ color: "#787b86" }}>Contract Strike:</div>
              <strong style={{ fontSize: "15px" }}>${activePos.strike || "PERP"}</strong>
            </div>
            <div>
              <div style={{ color: "#787b86" }}>Position Size:</div>
              <strong style={{ fontSize: "15px" }}>{activePos.size} contracts</strong>
            </div>
            <div>
              <div style={{ color: "#787b86" }}>Spot at Entry:</div>
              <strong style={{ fontSize: "15px" }}>${activePos.entry_spot?.toLocaleString()}</strong>
            </div>
            <div>
              <div style={{ color: "#787b86" }}>Order ID:</div>
              <code style={{ fontSize: "11px", color: "#FFCA28" }}>{activePos.order_id || "Active"}</code>
            </div>
          </div>
        </div>
      ) : (
        <div className="tv-panel" style={{ padding: "12px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: "12px", color: "#787b86" }}>
            Status: <strong style={{ color: "#00E676" }}>IDLE / MONITORING</strong> · Waiting for next Range Filter crossover trigger on {asset} ({timeframe})
          </span>
          <span style={{ fontSize: "11px", color: "#50535e" }}>Next BUY $\rightarrow$ Buy CALL | Next SELL $\rightarrow$ Buy PUT</span>
        </div>
      )}

      {/* Main Grid: Settings & Positions */}
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.3fr", gap: "16px" }}>
        {/* LEFT: Credentials & Strategy Settings */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* 1. Delta API Credentials */}
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Key size={14} style={{ color: "#2962ff" }} /> Delta Exchange API Authentication
              </span>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {balances.length > 0 && (
                  <span style={{ color: "#00E676", fontSize: "11px", fontWeight: 600 }}>
                    Bal: {balances[0]?.balance || 0} {balances[0]?.asset_symbol || "USDT"}
                  </span>
                )}
                {connStatus?.authenticated ? (
                  <span style={{ color: "#089981", display: "flex", alignItems: "center", gap: "4px", fontSize: "11px" }}>
                    <CheckCircle2 size={12} /> Authenticated
                  </span>
                ) : (
                  <span style={{ color: "#f23645", display: "flex", alignItems: "center", gap: "4px", fontSize: "11px" }}>
                    <XCircle size={12} /> Not Connected
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div className="form-group">
                <label>Exchange Region / Environment</label>
                <select
                  className="form-select"
                  value={environment}
                  onChange={(e) => setEnvironment(e.target.value as any)}
                >
                  <option value="testnet">Testnet Sandbox (Safe Testing - No Real Funds)</option>
                  <option value="global">Delta Exchange Global (api.delta.exchange)</option>
                  <option value="india">Delta Exchange India (india.delta.exchange)</option>
                </select>
              </div>

              <div className="form-group">
                <label>Delta API Key</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Enter your Delta API Key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Delta API Secret</label>
                <div style={{ display: "flex", gap: "6px" }}>
                  <input
                    type={showSecret ? "text" : "password"}
                    className="form-input"
                    placeholder="Enter your Delta API Secret"
                    value={apiSecret}
                    onChange={(e) => setApiSecret(e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowSecret((v) => !v)}
                    style={{ fontSize: "11px", whiteSpace: "nowrap" }}
                  >
                    {showSecret ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <button
                className="btn-primary"
                onClick={() => handleSaveConfig()}
                disabled={isLoading}
                style={{ marginTop: "4px" }}
              >
                {isLoading ? "Saving Credentials..." : "Save Credentials & Connect"}
              </button>
            </div>
          </div>

          {/* 2. Strategy & Execution Rules */}
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Zap size={14} style={{ color: "#FFCA28" }} /> Range Filter Execution Settings
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div className="form-group">
                  <label>Target Asset</label>
                  <select
                    className="form-select"
                    value={asset}
                    onChange={(e) => setAsset(e.target.value)}
                  >
                    <option value="BTC/USDT">BTC (Bitcoin)</option>
                    <option value="ETH/USDT">ETH (Ethereum)</option>
                    <option value="SOL/USDT">SOL (Solana)</option>
                    <option value="XRP/USDT">XRP (Ripple)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Signal Timeframe</label>
                  <select
                    className="form-select"
                    value={timeframe}
                    onChange={(e) => setTimeframe(e.target.value)}
                  >
                    <option value="5m">5 Minutes (Fast Scalp)</option>
                    <option value="15m">15 Minutes (Intraday)</option>
                    <option value="1h">1 Hour (Standard)</option>
                    <option value="4h">4 Hours (Swing)</option>
                  </select>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div className="form-group">
                  <label>Trading Product</label>
                  <select
                    className="form-select"
                    value={instrumentType}
                    onChange={(e) => setInstrumentType(e.target.value as any)}
                  >
                    <option value="options">Crypto Options (Call/Put)</option>
                    <option value="futures">Perpetual Futures (Long/Short)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Order Size (Contracts)</label>
                  <input
                    type="number"
                    min="1"
                    className="form-input"
                    value={sizeContracts}
                    onChange={(e) => setSizeContracts(parseInt(e.target.value) || 1)}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div className="form-group">
                  <label>Option Strike Selection</label>
                  <select
                    className="form-select"
                    value={strikeOffset}
                    onChange={(e) => setStrikeOffset(parseInt(e.target.value))}
                  >
                    <option value="0">ATM (At The Money)</option>
                    <option value="1">OTM +1 Strike (Higher Delta)</option>
                    <option value="-1">ITM -1 Strike (Lower Cost)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Hard Stop Loss (%)</label>
                  <input
                    type="number"
                    min="5"
                    max="100"
                    className="form-input"
                    value={stopLossPct}
                    onChange={(e) => setStopLossPct(parseFloat(e.target.value) || 50)}
                  />
                </div>
              </div>

              {/* Manual Trigger Buttons for Testing */}
              <div style={{ borderTop: "1px solid #2a2e39", paddingTop: "10px", marginTop: "4px" }}>
                <div style={{ fontSize: "11px", color: "#787b86", fontWeight: 700, marginBottom: "8px" }}>
                  🧪 MANUAL TRIGGER TESTS:
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <button
                    className="btn-secondary"
                    onClick={() => handleManualOrder("BUY")}
                    disabled={actionLoading}
                    style={{ color: "#089981", borderColor: "#089981", fontSize: "12px", fontWeight: 600 }}
                  >
                    Buy ATM Call Now
                  </button>
                  <button
                    className="btn-secondary"
                    onClick={() => handleManualOrder("SELL")}
                    disabled={actionLoading}
                    style={{ color: "#f23645", borderColor: "#f23645", fontSize: "12px", fontWeight: 600 }}
                  >
                    Buy ATM Put Now
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT: Live Open Positions & Execution Logs */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Live Open Positions Table */}
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                📊 Delta Exchange Open Positions ({positions.length})
              </span>
              <button
                className="btn-secondary"
                onClick={fetchStatusAndLogs}
                style={{ fontSize: "10px", padding: "2px 6px" }}
              >
                <RefreshCw size={10} /> Refresh
              </button>
            </div>

            {positions.length === 0 ? (
              <div style={{ textAlign: "center", padding: "30px 0", color: "#787b86", fontSize: "12px" }}>
                No active open positions on Delta Exchange.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="tv-table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Size</th>
                      <th>Entry Price</th>
                      <th>Mark Price</th>
                      <th>Unrealized PnL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((p, idx) => {
                      const pnl = parseFloat(p.unrealized_pnl || "0");
                      return (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600, color: "#fff" }}>
                            {p.product_symbol || p.symbol || `#${p.product_id}`}
                          </td>
                          <td style={{ color: parseInt(p.size) > 0 ? "#089981" : "#f23645" }}>
                            {p.size}
                          </td>
                          <td>${parseFloat(p.entry_price || "0").toFixed(2)}</td>
                          <td>${parseFloat(p.mark_price || "0").toFixed(2)}</td>
                          <td style={{ color: pnl >= 0 ? "#089981" : "#f23645", fontWeight: "bold" }}>
                            {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Trade Execution Audit Logs Stream */}
          <div className="tv-panel" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <div className="tv-panel-header">
              <span>📜 Real-Time Trade Execution Logs</span>
              <span style={{ color: "#089981", fontSize: "10px" }}>Live Stream</span>
            </div>

            <div
              style={{
                flex: 1,
                maxHeight: "340px",
                overflowY: "auto",
                backgroundColor: "#10121b",
                borderRadius: "4px",
                padding: "10px",
                fontSize: "11px",
                fontFamily: "monospace",
                display: "flex",
                flexDirection: "column",
                gap: "6px"
              }}
            >
              {logs.length === 0 ? (
                <div style={{ color: "#787b86", textAlign: "center", padding: "30px 0" }}>
                  Waiting for Auto-Trader triggers and events...
                </div>
              ) : (
                logs.map((log, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "6px 8px",
                      borderRadius: "3px",
                      backgroundColor: log.level === "error" ? "rgba(242, 54, 69, 0.15)" : log.level === "success" ? "rgba(8, 153, 129, 0.15)" : log.level === "warning" ? "rgba(255, 152, 0, 0.15)" : "#171b26",
                      borderLeft: `3px solid ${log.level === "error" ? "#f23645" : log.level === "success" ? "#089981" : log.level === "warning" ? "#FF9800" : "#2962ff"}`
                    }}
                  >
                    <span style={{ color: "#50535e", marginRight: "8px" }}>[{log.timestamp}]</span>
                    <span style={{ color: log.level === "error" ? "#f23645" : log.level === "success" ? "#089981" : log.level === "warning" ? "#FF9800" : "#d1d4dc" }}>
                      {log.message}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

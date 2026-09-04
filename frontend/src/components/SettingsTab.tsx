import React, { useState, useEffect } from "react";
import { Settings as SettingsIcon, Key, ShieldCheck, CheckCircle2, XCircle, RefreshCw, Eye, EyeOff, Save } from "lucide-react";
import { API_URL } from "../config";

export const SettingsTab: React.FC = () => {
  // Delta Credentials & Settings
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [savedSecretMasked, setSavedSecretMasked] = useState("");
  const [environment, setEnvironment] = useState<"testnet" | "global" | "india">("testnet");

  // Strategy & Risk Defaults
  const [defaultAsset, setDefaultAsset] = useState("BTC/USDT");
  const [defaultTimeframe, setDefaultTimeframe] = useState("1h");
  const [defaultInstrument, setDefaultInstrument] = useState<"options" | "futures">("options");
  const [defaultSize, setDefaultSize] = useState(1);
  const [defaultStrikeOffset, setDefaultStrikeOffset] = useState(0);
  const [defaultStopLoss, setDefaultStopLoss] = useState(50);

  // Status & Feedback
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [connResult, setConnResult] = useState<any>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState("");

  // Fetch saved settings on mount
  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_URL}/api/delta/settings`);
      if (res.ok) {
        const data = await res.json();
        if (data.api_key) setApiKey(data.api_key);
        if (data.api_secret_masked) setSavedSecretMasked(data.api_secret_masked);
        if (data.environment) setEnvironment(data.environment);
        if (data.asset) setDefaultAsset(data.asset);
        if (data.timeframe) setDefaultTimeframe(data.timeframe);
        if (data.instrument_type) setDefaultInstrument(data.instrument_type);
        if (data.size_contracts) setDefaultSize(data.size_contracts);
        if (data.strike_offset !== undefined) setDefaultStrikeOffset(data.strike_offset);
        if (data.stop_loss_pct) setDefaultStopLoss(data.stop_loss_pct);
      }
    } catch (err) {
      console.error("Error loading settings:", err);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  // Save Settings permanently
  const handleSaveSettings = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsSaving(true);
    setSaveSuccessMsg("");

    try {
      const payload: any = {
        environment,
        asset: defaultAsset,
        timeframe: defaultTimeframe,
        instrument_type: defaultInstrument,
        size_contracts: defaultSize,
        strike_offset: defaultStrikeOffset,
        stop_loss_pct: defaultStopLoss
      };

      if (apiKey.trim()) payload.api_key = apiKey.trim();
      if (apiSecret.trim()) payload.api_secret = apiSecret.trim();

      const res = await fetch(`${API_URL}/api/delta/save-settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        setSaveSuccessMsg("✅ Settings & Delta API keys saved permanently!");
        if (data.connection) {
          setConnResult(data.connection);
        }
        await fetchSettings();
        if (apiSecret.trim()) {
          setApiSecret(""); // Clear plaintext secret field once saved
        }
        setTimeout(() => setSaveSuccessMsg(""), 5000);
      } else {
        throw new Error("Failed to save settings");
      }
    } catch (err: any) {
      alert(`Error saving settings: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Test API connection
  const handleTestConnection = async () => {
    setIsTesting(true);
    setConnResult(null);
    try {
      const res = await fetch(`${API_URL}/api/delta/test-connection`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        setConnResult(data.connection);
      }
    } catch (err) {
      console.error("Test connection failed:", err);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #2a2e39", paddingBottom: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <SettingsIcon size={24} style={{ color: "#2962ff" }} />
          <div>
            <h2 style={{ margin: 0, fontSize: "20px", color: "#f0f3fa" }}>Platform & Delta Exchange Settings</h2>
            <div style={{ fontSize: "12px", color: "#787b86" }}>
              Configure and persist your Delta Exchange API credentials and trading preferences
            </div>
          </div>
        </div>

        {saveSuccessMsg && (
          <div style={{ color: "#089981", fontSize: "13px", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
            <CheckCircle2 size={16} /> {saveSuccessMsg}
          </div>
        )}
      </div>

      <form onSubmit={handleSaveSettings} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        {/* 1. DELTA EXCHANGE CREDENTIALS CARD */}
        <div className="tv-panel">
          <div className="tv-panel-header">
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Key size={15} style={{ color: "#2962ff" }} /> 1. Delta Exchange API Credentials
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {connResult?.authenticated ? (
                <span style={{ color: "#089981", fontSize: "11px", fontWeight: 700, display: "flex", alignItems: "center", gap: "4px" }}>
                  <CheckCircle2 size={13} /> Connected & Authenticated
                </span>
              ) : connResult?.connected === false ? (
                <span style={{ color: "#f23645", fontSize: "11px", fontWeight: 700, display: "flex", alignItems: "center", gap: "4px" }}>
                  <XCircle size={13} /> Connection Failed
                </span>
              ) : null}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div className="form-group">
              <label>Exchange Region / Environment</label>
              <select
                className="form-select"
                value={environment}
                onChange={(e) => setEnvironment(e.target.value as any)}
              >
                <option value="testnet">Testnet Sandbox (testnet-api.delta.exchange) — Recommended for Safe Testing</option>
                <option value="india">Delta Exchange India (india.delta.exchange) — Live INR / F&O</option>
                <option value="global">Delta Exchange Global (api.delta.exchange) — Live Global USDT</option>
              </select>
              <div style={{ fontSize: "11px", color: "#787b86", marginTop: "4px" }}>
                Select <strong>Testnet Sandbox</strong> for risk-free simulation, or <strong>Delta India / Global</strong> for live real-money order execution.
              </div>
            </div>

            <div className="form-group">
              <label>Delta API Key</label>
              <input
                type="text"
                className="form-input"
                placeholder="Paste your Delta Exchange API Key here"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Delta API Secret</label>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type={showSecret ? "text" : "password"}
                  className="form-input"
                  placeholder={savedSecretMasked ? `Saved: ${savedSecretMasked} (Enter new secret to overwrite)` : "Paste your Delta Exchange API Secret here"}
                  value={apiSecret}
                  onChange={(e) => setApiSecret(e.target.value)}
                />
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowSecret((v) => !v)}
                  style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "12px", whiteSpace: "nowrap" }}
                >
                  {showSecret ? <EyeOff size={13} /> : <Eye size={13} />}
                  {showSecret ? "Hide" : "Show"}
                </button>
              </div>
              {savedSecretMasked && !apiSecret && (
                <div style={{ fontSize: "11px", color: "#00E676", marginTop: "4px" }}>
                  🔒 An API Secret is currently saved securely on the backend ({savedSecretMasked}).
                </div>
              )}
            </div>

            <div style={{ display: "flex", gap: "10px", marginTop: "6px" }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleTestConnection}
                disabled={isTesting}
                style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", padding: "8px 16px" }}
              >
                <RefreshCw size={13} className={isTesting ? "spin" : ""} />
                {isTesting ? "Testing API Connection..." : "Test Connection & Balance"}
              </button>
            </div>

            {connResult && (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "4px",
                  backgroundColor: connResult.authenticated ? "rgba(8, 153, 129, 0.15)" : "rgba(242, 54, 69, 0.15)",
                  border: `1px solid ${connResult.authenticated ? "#089981" : "#f23645"}`,
                  fontSize: "12px",
                  color: connResult.authenticated ? "#089981" : "#f23645"
                }}
              >
                {connResult.message}
              </div>
            )}
          </div>
        </div>

        {/* 2. AUTO-TRADING & RISK EXECUTION DEFAULTS */}
        <div className="tv-panel">
          <div className="tv-panel-header">
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <ShieldCheck size={15} style={{ color: "#FFCA28" }} /> 2. Strategy & Range Filter Execution Defaults
            </span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div className="form-group">
              <label>Default Trading Asset</label>
              <select
                className="form-select"
                value={defaultAsset}
                onChange={(e) => setDefaultAsset(e.target.value)}
              >
                <option value="BTC/USDT">BTC (Bitcoin)</option>
                <option value="ETH/USDT">ETH (Ethereum)</option>
                <option value="SOL/USDT">SOL (Solana)</option>
                <option value="XRP/USDT">XRP (Ripple)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Signal Trigger Timeframe</label>
              <select
                className="form-select"
                value={defaultTimeframe}
                onChange={(e) => setDefaultTimeframe(e.target.value)}
              >
                <option value="5m">5 Minutes (Scalp)</option>
                <option value="15m">15 Minutes (Intraday)</option>
                <option value="1h">1 Hour (Standard)</option>
                <option value="4h">4 Hours (Swing)</option>
                <option value="1d">1 Day (Macro)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Trading Product Type</label>
              <select
                className="form-select"
                value={defaultInstrument}
                onChange={(e) => setDefaultInstrument(e.target.value as any)}
              >
                <option value="options">Crypto Options (Call on Buy / Put on Sell)</option>
                <option value="futures">Perpetual Futures (Long on Buy / Short on Sell)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Default Order Size (Contracts)</label>
              <input
                type="number"
                min="1"
                className="form-input"
                value={defaultSize}
                onChange={(e) => setDefaultSize(parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="form-group">
              <label>Option Strike Selection Distance</label>
              <select
                className="form-select"
                value={defaultStrikeOffset}
                onChange={(e) => setDefaultStrikeOffset(parseInt(e.target.value))}
              >
                <option value="0">ATM (At The Money — Best Delta & Liquidity)</option>
                <option value="1">OTM +1 Strike (Higher Leverage / Cheaper)</option>
                <option value="-1">ITM -1 Strike (Lower Volatility)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Hard Stop Loss (%)</label>
              <input
                type="number"
                min="5"
                max="100"
                className="form-input"
                value={defaultStopLoss}
                onChange={(e) => setDefaultStopLoss(parseFloat(e.target.value) || 50)}
              />
            </div>
          </div>
        </div>

        {/* 3. PERSISTENCE ACTIONS */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", borderTop: "1px solid #2a2e39", paddingTop: "16px" }}>
          <button
            type="submit"
            className="btn-primary"
            disabled={isSaving}
            style={{
              width: "auto",
              padding: "10px 28px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontSize: "14px",
              fontWeight: 700
            }}
          >
            <Save size={16} />
            {isSaving ? "Saving Settings..." : "Save All Settings"}
          </button>
        </div>
      </form>
    </div>
  );
};

import React, { useState, useEffect } from "react";
import { PhoneCall, PhoneForwarded, Radio, Users, Plus, Trash2, RefreshCw, Sparkles, Activity, DollarSign } from "lucide-react";
import { API_URL } from "../config";

interface Subscriber {
  name: string;
  phone: string;
  assets: string[];
  enabled: boolean;
  total_calls?: number;
  last_called?: string | null;
}

interface VoiceAlertsTabProps {
  activeSymbol: string;
}

export const VoiceAlertsTab: React.FC<VoiceAlertsTabProps> = ({ activeSymbol }) => {
  // Status state
  const [voiceStatus, setVoiceStatus] = useState<any>(null);
  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [calls, setCalls] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Test Call state with localStorage persistence
  const [testPhone, setTestPhone] = useState(() => {
    return localStorage.getItem("stellar_voice_test_phone") || "+91";
  });
  const [testAsset, setTestAsset] = useState(activeSymbol || "BTC/USDT");
  const [testSignal, setTestSignal] = useState<"BUY" | "SELL">("BUY");
  const [testTimeframe, setTestTimeframe] = useState("1h");
  const [isCalling, setIsCalling] = useState(false);
  const [callFeedback, setCallFeedback] = useState<any>(null);

  useEffect(() => {
    try {
      localStorage.setItem("stellar_voice_test_phone", testPhone);
    } catch (e) {}
  }, [testPhone]);

  // Add Subscriber Form state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("+91");
  const [newAssets, setNewAssets] = useState("ALL");
  const [isSavingSub, setIsSavingSub] = useState(false);

  // Selected Call Modal for Transcript
  const [selectedCall, setSelectedCall] = useState<any>(null);

  const fetchStatusAndData = async () => {
    setIsLoading(true);
    try {
      const [resStatus, resSubs, resCalls] = await Promise.all([
        fetch(`${API_URL}/api/voice/status`),
        fetch(`${API_URL}/api/voice/subscribers`),
        fetch(`${API_URL}/api/voice/calls?limit=10`)
      ]);

      if (resStatus.ok) setVoiceStatus(await resStatus.json());
      if (resSubs.ok) setSubscribers(await resSubs.json());
      if (resCalls.ok) setCalls(await resCalls.json());
    } catch (e) {
      console.error("Error fetching voice data:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatusAndData();
    const interval = setInterval(fetchStatusAndData, 20000);
    return () => clearInterval(interval);
  }, []);

  const handleTestCall = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testPhone || testPhone.length < 10) {
      setCallFeedback({ success: false, error: "Please enter a valid phone number with country code (e.g. +919876543210)" });
      return;
    }

    setIsCalling(true);
    setCallFeedback(null);

    try {
      const res = await fetch(`${API_URL}/api/voice/test-call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: testPhone,
          asset: testAsset,
          signal: testSignal,
          timeframe: testTimeframe
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setCallFeedback({
          success: true,
          message: `📞 Call successfully initiated to ${data.to_number}! Caller ID: ${data.from_number || "+918071581407"}. Call ID: ${data.call_id}`
        });
        fetchStatusAndData();
      } else {
        setCallFeedback({
          success: false,
          error: data.error || data.detail || "Outbound call failed. Please check wallet balance and phone format."
        });
      }
    } catch (err: any) {
      setCallFeedback({ success: false, error: err.message || "Failed to trigger call." });
    } finally {
      setIsCalling(false);
    }
  };

  const handleAddSubscriber = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPhone || newPhone.length < 10 || !newName) return;

    setIsSavingSub(true);
    try {
      const assetList = newAssets.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
      const res = await fetch(`${API_URL}/api/voice/subscribers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName,
          phone: newPhone,
          assets: assetList.length > 0 ? assetList : ["ALL"],
          enabled: true
        })
      });

      if (res.ok) {
        setShowAddModal(false);
        setNewName("");
        setNewPhone("+91");
        setNewAssets("ALL");
        fetchStatusAndData();
      }
    } catch (err) {
      console.error("Error adding subscriber:", err);
    } finally {
      setIsSavingSub(false);
    }
  };

  const handleToggleSubscriber = async (sub: Subscriber) => {
    try {
      await fetch(`${API_URL}/api/voice/subscribers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: sub.name,
          phone: sub.phone,
          assets: sub.assets,
          enabled: !sub.enabled
        })
      });
      fetchStatusAndData();
    } catch (err) {
      console.error("Error toggling subscriber:", err);
    }
  };

  const handleDeleteSubscriber = async (phone: string) => {
    if (!confirm(`Remove subscriber ${phone}?`)) return;
    try {
      await fetch(`${API_URL}/api/voice/subscribers/${encodeURIComponent(phone)}`, {
        method: "DELETE"
      });
      fetchStatusAndData();
    } catch (err) {
      console.error("Error removing subscriber:", err);
    }
  };

  const wallet = voiceStatus?.wallet;
  const balanceInr = wallet?.balanceInr ?? ((wallet?.balanceCents ?? 0) / 100);
  const callerNumber = voiceStatus?.phone_numbers?.[0]?.number || "+918071581407";
  const agentName = voiceStatus?.agent?.name || "Stellar Quant Voice Trader";

  return (
    <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "10px 0" }}>
      {/* Top Banner & Wallet Status */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "16px",
          marginBottom: "24px"
        }}
      >
        {/* Status Card */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(15, 23, 42, 0.6))",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: "12px",
            padding: "18px"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>
              <Radio size={16} color="#10b981" />
              SNAPSERVE VOICE AI
            </div>
            <span
              style={{
                fontSize: "11px",
                padding: "2px 8px",
                borderRadius: "10px",
                background: "rgba(16, 185, 129, 0.2)",
                color: "#10b981",
                fontWeight: 700
              }}
            >
              ACTIVE & LIVE
            </span>
          </div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc", marginBottom: "4px" }}>
            {agentName}
          </div>
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            Agent ID: <strong style={{ color: "#38bdf8" }}>#{voiceStatus?.agent_id || 1081}</strong> • Indic Multilingual
          </div>
        </div>

        {/* Wallet Balance Card */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(15, 23, 42, 0.6))",
            border: "1px solid rgba(56, 189, 248, 0.3)",
            borderRadius: "12px",
            padding: "18px"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>
              <DollarSign size={16} color="#38bdf8" />
              PREPAID VOICE WALLET
            </div>
            <button
              onClick={fetchStatusAndData}
              style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer" }}
              title="Refresh"
            >
              <RefreshCw size={14} className={isLoading ? "spin" : ""} />
            </button>
          </div>
          <div style={{ fontSize: "22px", fontWeight: 800, color: "#38bdf8", marginBottom: "4px" }}>
            ₹{balanceInr.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            Rate: ₹5.00/min • Approx. ~{Math.floor(balanceInr / 5)} calling minutes available
          </div>
        </div>

        {/* Caller ID & Stack */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(168, 85, 247, 0.12), rgba(15, 23, 42, 0.6))",
            border: "1px solid rgba(168, 85, 247, 0.3)",
            borderRadius: "12px",
            padding: "18px"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>
              <PhoneForwarded size={16} color="#c084fc" />
              OUTBOUND CALLER ID
            </div>
          </div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc", marginBottom: "4px" }}>
            {callerNumber}
          </div>
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            Sarvam STT + Groq LLaMA 3.3 70B + Cartesia Sonic
          </div>
        </div>

        {/* Subscribers Count */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(15, 23, 42, 0.6))",
            border: "1px solid rgba(245, 158, 11, 0.3)",
            borderRadius: "12px",
            padding: "18px"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>
              <Users size={16} color="#fbbf24" />
              SUBSCRIBED TRADERS
            </div>
          </div>
          <div style={{ fontSize: "22px", fontWeight: 800, color: "#fbbf24", marginBottom: "4px" }}>
            {subscribers.filter((s) => s.enabled).length} <span style={{ fontSize: "14px", color: "#94a3b8", fontWeight: 400 }}>/ {subscribers.length} total</span>
          </div>
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            Auto-called on Range Filter Buy/Sell signals
          </div>
        </div>
      </div>

      {/* Main 2-Column Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: "24px" }}>
        {/* Left Column: Instant Live Test Call */}
        <div
          style={{
            background: "#131722",
            border: "1px solid #2a2e39",
            borderRadius: "14px",
            padding: "24px"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <PhoneCall size={20} color="#2962ff" />
            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>
              Instant AI Voice Call Dispatcher
            </h3>
          </div>

          <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "20px", lineHeight: "1.5" }}>
            Test placing an immediate outbound phone call to any customer or your own number. The SnapServe Voice Agent will speak dynamically, delivering the live <strong>Range Filter Signal</strong>, entry spot price, Stop Loss & Take Profit targets, Smart Money Concepts (SMC) order blocks, news sentiment, and AI forecast.
          </p>

          <form onSubmit={handleTestCall}>
            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#94a3b8", marginBottom: "6px" }}>
                CUSTOMER / DESTINATION PHONE NUMBER (E.164)
              </label>
              <input
                type="text"
                value={testPhone}
                onChange={(e) => setTestPhone(e.target.value)}
                placeholder="+919876543210"
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  background: "#1e222d",
                  border: "1px solid #363c4e",
                  borderRadius: "8px",
                  color: "#f8fafc",
                  fontSize: "14px",
                  fontFamily: "monospace"
                }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: "12px", marginBottom: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#94a3b8", marginBottom: "6px" }}>
                  ASSET SYMBOL
                </label>
                <select
                  value={testAsset}
                  onChange={(e) => setTestAsset(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    background: "#1e222d",
                    border: "1px solid #363c4e",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "13px"
                  }}
                >
                  <option value="BTC/USDT">BTC/USDT (Bitcoin)</option>
                  <option value="ETH/USDT">ETH/USDT (Ethereum)</option>
                  <option value="XAUT/USDT">XAUT/USDT (Tether Gold)</option>
                  <option value="SOL/USDT">SOL/USDT (Solana)</option>
                  <option value="XRP/USDT">XRP/USDT (Ripple)</option>
                  <option value="AAPL">AAPL (Apple Inc.)</option>
                  <option value="^NSEI">^NSEI (Nifty 50 Index)</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#94a3b8", marginBottom: "6px" }}>
                  TIMEFRAME
                </label>
                <select
                  value={testTimeframe}
                  onChange={(e) => setTestTimeframe(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    background: "#1e222d",
                    border: "1px solid #363c4e",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "13px"
                  }}
                >
                  <option value="15m">15 Minutes</option>
                  <option value="1h">1 Hour (Std)</option>
                  <option value="4h">4 Hours</option>
                  <option value="1d">1 Day</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#94a3b8", marginBottom: "6px" }}>
                  SIGNAL TYPE
                </label>
                <div style={{ display: "flex", gap: "6px" }}>
                  <button
                    type="button"
                    onClick={() => setTestSignal("BUY")}
                    style={{
                      flex: 1,
                      padding: "9px 0",
                      borderRadius: "8px",
                      border: "none",
                      background: testSignal === "BUY" ? "#10b981" : "#1e222d",
                      color: "#fff",
                      fontWeight: 700,
                      fontSize: "12px",
                      cursor: "pointer"
                    }}
                  >
                    BUY
                  </button>
                  <button
                    type="button"
                    onClick={() => setTestSignal("SELL")}
                    style={{
                      flex: 1,
                      padding: "9px 0",
                      borderRadius: "8px",
                      border: "none",
                      background: testSignal === "SELL" ? "#ef4444" : "#1e222d",
                      color: "#fff",
                      fontWeight: 700,
                      fontSize: "12px",
                      cursor: "pointer"
                    }}
                  >
                    SELL
                  </button>
                </div>
              </div>
            </div>

            {/* Live Call Context Preview Box */}
            <div
              style={{
                background: "rgba(30, 34, 45, 0.7)",
                border: "1px solid #2a2e39",
                borderRadius: "8px",
                padding: "12px",
                marginBottom: "20px",
                fontSize: "12px",
                color: "#cbd5e1"
              }}
            >
              <div style={{ fontWeight: 600, color: "#38bdf8", marginBottom: "4px", display: "flex", alignItems: "center", gap: "4px" }}>
                <Sparkles size={14} /> AI Voice Speech Rationale Preview:
              </div>
              <div style={{ fontStyle: "italic", color: "#94a3b8" }}>
                "Hello! This is your Stellar Quant AI Voice Dispatcher with an urgent live {testSignal} signal alert on {testAsset}. Key invalidation Stop Loss and Take Profit levels calculated from real-time Order Blocks, Volume Profile, and news sentiment score."
              </div>
            </div>

            {/* Feedback Alert */}
            {callFeedback && (
              <div
                style={{
                  padding: "12px",
                  borderRadius: "8px",
                  marginBottom: "16px",
                  fontSize: "13px",
                  background: callFeedback.success ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                  border: `1px solid ${callFeedback.success ? "#10b981" : "#ef4444"}`,
                  color: callFeedback.success ? "#34d399" : "#f87171"
                }}
              >
                {callFeedback.success ? callFeedback.message : `Error: ${callFeedback.error}`}
              </div>
            )}

            <button
              type="submit"
              disabled={isCalling}
              style={{
                width: "100%",
                padding: "12px",
                borderRadius: "8px",
                border: "none",
                background: isCalling ? "#475569" : "linear-gradient(135deg, #2563eb, #1d4ed8)",
                color: "#fff",
                fontWeight: 700,
                fontSize: "14px",
                cursor: isCalling ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                boxShadow: "0 4px 12px rgba(37, 99, 235, 0.3)"
              }}
            >
              {isCalling ? (
                <>
                  <RefreshCw size={16} className="spin" />
                  Connecting to Telephony & Dialing...
                </>
              ) : (
                <>
                  <PhoneCall size={16} />
                  🚀 Trigger Live AI Voice Call Now
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Column: Subscribed VIP Customers */}
        <div
          style={{
            background: "#131722",
            border: "1px solid #2a2e39",
            borderRadius: "14px",
            padding: "24px",
            display: "flex",
            flexDirection: "column"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Users size={20} color="#fbbf24" />
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>
                Subscribed VIP Traders ({subscribers.length})
              </h3>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              style={{
                background: "#2563eb",
                border: "none",
                borderRadius: "6px",
                color: "#fff",
                padding: "6px 12px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "4px"
              }}
            >
              <Plus size={14} /> Add Customer
            </button>
          </div>

          <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>
            Whenever the Range Filter auto-trading engine detects a BUY or SELL signal on BTC, ETH, or Gold, the system automatically calls these numbers immediately.
          </p>

          {/* Subscribers List */}
          <div style={{ flex: 1, overflowY: "auto", maxHeight: "380px" }}>
            {subscribers.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 0", color: "#64748b", fontSize: "13px" }}>
                No subscribers registered yet. Click <strong>+ Add Customer</strong> to enroll phone numbers for automated signal phone calls.
              </div>
            ) : (
              subscribers.map((sub, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px",
                    background: "#1e222d",
                    border: "1px solid #2a2e39",
                    borderRadius: "8px",
                    marginBottom: "8px"
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <strong style={{ color: "#f8fafc", fontSize: "14px" }}>{sub.name}</strong>
                      <span
                        style={{
                          fontSize: "10px",
                          padding: "1px 6px",
                          borderRadius: "4px",
                          background: sub.enabled ? "rgba(16, 185, 129, 0.2)" : "rgba(100, 116, 139, 0.2)",
                          color: sub.enabled ? "#10b981" : "#94a3b8",
                          fontWeight: 700
                        }}
                      >
                        {sub.enabled ? "ACTIVE" : "PAUSED"}
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", color: "#38bdf8", fontFamily: "monospace", marginTop: "2px" }}>
                      {sub.phone}
                    </div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                      Assets: {sub.assets.join(", ")} • Total Calls: {sub.total_calls || 0}
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <button
                      onClick={() => handleToggleSubscriber(sub)}
                      style={{
                        background: sub.enabled ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)",
                        border: "none",
                        color: sub.enabled ? "#ef4444" : "#10b981",
                        borderRadius: "6px",
                        padding: "4px 8px",
                        fontSize: "11px",
                        fontWeight: 600,
                        cursor: "pointer"
                      }}
                    >
                      {sub.enabled ? "Pause" : "Enable"}
                    </button>
                    <button
                      onClick={() => handleDeleteSubscriber(sub.phone)}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "#64748b",
                        cursor: "pointer",
                        padding: "4px"
                      }}
                      title="Delete"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Add Subscriber Modal */}
      {showAddModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999
          }}
        >
          <div
            style={{
              background: "#1e222d",
              border: "1px solid #363c4e",
              borderRadius: "12px",
              padding: "24px",
              width: "100%",
              maxWidth: "420px"
            }}
          >
            <h3 style={{ margin: "0 0 16px 0", fontSize: "16px", color: "#f8fafc" }}>
              Add VIP Trader for Voice Alerts
            </h3>

            <form onSubmit={handleAddSubscriber}>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#94a3b8", marginBottom: "6px" }}>
                  CUSTOMER / TRADER NAME
                </label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    background: "#131722",
                    border: "1px solid #363c4e",
                    borderRadius: "6px",
                    color: "#f8fafc",
                    fontSize: "13px"
                  }}
                />
              </div>

              <div style={{ marginBottom: "14px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#94a3b8", marginBottom: "6px" }}>
                  PHONE NUMBER (WITH COUNTRY CODE)
                </label>
                <input
                  type="text"
                  required
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  placeholder="+919876543210"
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    background: "#131722",
                    border: "1px solid #363c4e",
                    borderRadius: "6px",
                    color: "#f8fafc",
                    fontSize: "13px",
                    fontFamily: "monospace"
                  }}
                />
              </div>

              <div style={{ marginBottom: "20px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#94a3b8", marginBottom: "6px" }}>
                  SUBSCRIBED ASSETS (COMMA SEPARATED)
                </label>
                <input
                  type="text"
                  value={newAssets}
                  onChange={(e) => setNewAssets(e.target.value)}
                  placeholder="ALL, or BTC/USDT, ETH/USDT, XAUT"
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    background: "#131722",
                    border: "1px solid #363c4e",
                    borderRadius: "6px",
                    color: "#f8fafc",
                    fontSize: "13px"
                  }}
                />
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  style={{
                    background: "transparent",
                    border: "1px solid #475569",
                    color: "#94a3b8",
                    padding: "8px 16px",
                    borderRadius: "6px",
                    cursor: "pointer"
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingSub}
                  style={{
                    background: "#2563eb",
                    border: "none",
                    color: "#fff",
                    padding: "8px 18px",
                    borderRadius: "6px",
                    fontWeight: 600,
                    cursor: "pointer"
                  }}
                >
                  {isSavingSub ? "Saving..." : "Save Subscriber"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Recent Outbound Calls & Transcripts History */}
      <div
        style={{
          background: "#131722",
          border: "1px solid #2a2e39",
          borderRadius: "14px",
          padding: "24px",
          marginTop: "24px"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Activity size={20} color="#38bdf8" />
            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>
              Live SnapServe Call Logs & Transcripts
            </h3>
          </div>
          <button
            onClick={fetchStatusAndData}
            style={{
              background: "#1e222d",
              border: "1px solid #363c4e",
              borderRadius: "6px",
              color: "#94a3b8",
              padding: "6px 12px",
              fontSize: "12px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "4px"
            }}
          >
            <RefreshCw size={14} className={isLoading ? "spin" : ""} /> Refresh History
          </button>
        </div>

        {calls.length === 0 ? (
          <div style={{ textAlign: "center", padding: "30px 0", color: "#64748b", fontSize: "13px" }}>
            No calls recorded yet. Trigger a test call or wait for Range Filter auto-trading triggers.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #2a2e39", color: "#94a3b8", textAlign: "left" }}>
                  <th style={{ padding: "10px" }}>CALL ID</th>
                  <th style={{ padding: "10px" }}>TO NUMBER</th>
                  <th style={{ padding: "10px" }}>STATUS</th>
                  <th style={{ padding: "10px" }}>DURATION</th>
                  <th style={{ padding: "10px" }}>COST</th>
                  <th style={{ padding: "10px" }}>AI SUMMARY / TRANSCRIPT</th>
                </tr>
              </thead>
              <tbody>
                {calls.map((c, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid #1e222d" }}>
                    <td style={{ padding: "10px", color: "#38bdf8", fontFamily: "monospace" }}>#{c.id}</td>
                    <td style={{ padding: "10px", color: "#f8fafc", fontFamily: "monospace" }}>{c.toNumber}</td>
                    <td style={{ padding: "10px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          padding: "2px 8px",
                          borderRadius: "6px",
                          fontWeight: 700,
                          background:
                            c.status === "completed"
                              ? "rgba(16, 185, 129, 0.2)"
                              : c.status === "failed"
                              ? "rgba(239, 68, 68, 0.2)"
                              : "rgba(245, 158, 11, 0.2)",
                          color:
                            c.status === "completed"
                              ? "#10b981"
                              : c.status === "failed"
                              ? "#ef4444"
                              : "#fbbf24"
                        }}
                      >
                        {c.status?.toUpperCase() || "INITIATED"}
                      </span>
                    </td>
                    <td style={{ padding: "10px", color: "#94a3b8" }}>{c.durationSeconds ? `${c.durationSeconds}s` : "-"}</td>
                    <td style={{ padding: "10px", color: "#94a3b8" }}>{c.costCents ? `₹${(c.costCents / 100).toFixed(2)}` : "-"}</td>
                    <td style={{ padding: "10px" }}>
                      {c.transcript || c.callSummary ? (
                        <button
                          onClick={() => setSelectedCall(c)}
                          style={{
                            background: "rgba(56, 189, 248, 0.15)",
                            border: "1px solid #38bdf8",
                            color: "#38bdf8",
                            padding: "4px 10px",
                            borderRadius: "6px",
                            fontSize: "11px",
                            fontWeight: 600,
                            cursor: "pointer"
                          }}
                        >
                          View Transcript
                        </button>
                      ) : (
                        <span style={{ color: "#64748b", fontSize: "12px" }}>In progress...</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Transcript Modal */}
      {selectedCall && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px"
          }}
        >
          <div
            style={{
              background: "#1e222d",
              border: "1px solid #363c4e",
              borderRadius: "14px",
              padding: "24px",
              width: "100%",
              maxWidth: "600px",
              maxHeight: "80vh",
              display: "flex",
              flexDirection: "column"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ margin: 0, fontSize: "16px", color: "#f8fafc" }}>
                Call #{selectedCall.id} Transcript ({selectedCall.toNumber})
              </h3>
              <button
                onClick={() => setSelectedCall(null)}
                style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "18px" }}
              >
                ✕
              </button>
            </div>

            {selectedCall.callSummary && (
              <div
                style={{
                  background: "rgba(56, 189, 248, 0.1)",
                  border: "1px solid rgba(56, 189, 248, 0.3)",
                  borderRadius: "8px",
                  padding: "12px",
                  marginBottom: "16px",
                  fontSize: "13px",
                  color: "#cbd5e1"
                }}
              >
                <strong>AI Call Summary:</strong> {selectedCall.callSummary}
              </div>
            )}

            <div
              style={{
                flex: 1,
                overflowY: "auto",
                background: "#131722",
                padding: "14px",
                borderRadius: "8px",
                border: "1px solid #2a2e39",
                fontFamily: "monospace",
                fontSize: "13px",
                color: "#e2e8f0",
                whiteSpace: "pre-wrap"
              }}
            >
              {selectedCall.transcript || "No transcript available."}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

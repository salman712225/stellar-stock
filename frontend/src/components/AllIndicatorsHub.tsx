import React, { useState } from "react";
import { Activity, TrendingUp, Zap, Gauge, BarChart2, Compass, Layers } from "lucide-react";

interface AllIndicatorsHubProps {
  analysisData: any;
  activeSymbol: string;
}

export const AllIndicatorsHub: React.FC<AllIndicatorsHubProps> = ({ analysisData, activeSymbol }) => {
  const [activeCategory, setActiveCategory] = useState<"all" | "trend" | "momentum" | "volatility" | "volume" | "smc" | "patterns">("all");

  if (!analysisData || !analysisData.indicators) {
    return (
      <div style={{ textAlign: "center", padding: "60px 0", color: "#787b86" }}>
        No indicator dataset available for {activeSymbol}.
      </div>
    );
  }

  const latest = analysisData.indicators.latest || {};
  const currentPrice = analysisData.current_price || 0;
  const pivots = analysisData.indicators.pivots || {};
  const smc = analysisData.smc || {};
  const patterns = analysisData.patterns || {};
  const vp = analysisData.indicators.volume_profile || {};

  // Helper for pill badge
  const renderStatus = (condition: "bullish" | "bearish" | "neutral", text?: string) => {
    const label = text || condition.toUpperCase();
    if (condition === "bullish") {
      return <span className="badge-buy">{label}</span>;
    } else if (condition === "bearish") {
      return <span className="badge-sell">{label}</span>;
    }
    return <span className="badge-hold">{label}</span>;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Category Filter Pills */}
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", borderBottom: "1px solid #2a2e39", paddingBottom: "12px" }}>
        {[
          { id: "all", label: "All Indicators", icon: <Layers size={13} /> },
          { id: "trend", label: "Trend & Moving Averages", icon: <TrendingUp size={13} /> },
          { id: "momentum", label: "Momentum & Oscillators", icon: <Zap size={13} /> },
          { id: "volatility", label: "Volatility & Bands", icon: <Activity size={13} /> },
          { id: "volume", label: "Volume & Liquidity", icon: <BarChart2 size={13} /> },
          { id: "smc", label: "Smart Money (SMC)", icon: <Compass size={13} /> },
          { id: "patterns", label: "Candlestick Patterns", icon: <Gauge size={13} /> },
        ].map((cat) => (
          <button
            key={cat.id}
            className={`btn-secondary ${activeCategory === cat.id ? "active" : ""}`}
            onClick={() => setActiveCategory(cat.id as any)}
            style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
          >
            {cat.icon} {cat.label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
        {/* 1. TREND & MOVING AVERAGES */}
        {(activeCategory === "all" || activeCategory === "trend") && (
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <TrendingUp size={14} style={{ color: "#2962ff" }} /> 1. Trend & Directional Indicators
              </span>
            </div>
            <div className="indicator-list">
              <div className="indicator-row">
                <span className="ind-name">Supertrend</span>
                <span className="ind-val">${latest.supertrend?.toLocaleString(undefined, { maximumFractionDigits: 4 })}</span>
                {renderStatus(latest.direction === 1 ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Range Filter Buy/Sell</span>
                <span className="ind-val">${latest.range_filter?.toLocaleString(undefined, { maximumFractionDigits: 4 })}</span>
                {renderStatus(latest.range_direction === 1 ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Ichimoku Cloud</span>
                <span className="ind-val">Tenkan: ${latest.ichimoku_tenkan?.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                {renderStatus(latest.ichimoku_cloud === "bullish" ? "bullish" : "bearish", latest.ichimoku_cloud?.toUpperCase())}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Parabolic SAR</span>
                <span className="ind-val">${latest.parabolic_sar?.toLocaleString(undefined, { maximumFractionDigits: 4 })}</span>
                {renderStatus(currentPrice > latest.parabolic_sar ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">ADX (Trend Strength)</span>
                <span className="ind-val">{latest.adx?.toFixed(1)} (+DI: {latest.plus_di?.toFixed(1)}, -DI: {latest.minus_di?.toFixed(1)})</span>
                {renderStatus(latest.plus_di > latest.minus_di ? "bullish" : "bearish", latest.adx > 25 ? "STRONG TREND" : "WEAK / RANGE")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">MACD (12, 26, 9)</span>
                <span className="ind-val">Hist: {latest.macd_hist?.toFixed(4)}</span>
                {renderStatus(latest.macd_hist > 0 ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">EMA 9 / EMA 21</span>
                <span className="ind-val">${latest.ema_9?.toFixed(2)} / ${latest.ema_21?.toFixed(2)}</span>
                {renderStatus(latest.ema_9 > latest.ema_21 ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">SMA 50 / SMA 200</span>
                <span className="ind-val">${latest.sma_50?.toFixed(2)} / ${latest.sma_200?.toFixed(2)}</span>
                {renderStatus(latest.sma_50 > latest.sma_200 ? "bullish" : "bearish", latest.sma_50 > latest.sma_200 ? "GOLDEN CROSS" : "DEATH CROSS")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Hull Moving Avg (HMA 20)</span>
                <span className="ind-val">${latest.hma_20?.toFixed(2)}</span>
                {renderStatus(currentPrice > latest.hma_20 ? "bullish" : "bearish")}
              </div>
            </div>
          </div>
        )}

        {/* 2. MOMENTUM & OSCILLATORS */}
        {(activeCategory === "all" || activeCategory === "momentum") && (
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Zap size={14} style={{ color: "#FFCA28" }} /> 2. Momentum Oscillators & Divergences
              </span>
            </div>
            <div className="indicator-list">
              <div className="indicator-row">
                <span className="ind-name">RSI (14-period)</span>
                <span className="ind-val">{latest.rsi_14?.toFixed(1)}</span>
                {renderStatus(latest.rsi_14 > 70 ? "bearish" : latest.rsi_14 < 30 ? "bullish" : "neutral", latest.rsi_14 > 70 ? "OVERBOUGHT" : latest.rsi_14 < 30 ? "OVERSOLD" : "NEUTRAL")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">RSI (7-period Fast)</span>
                <span className="ind-val">{latest.rsi_7?.toFixed(1)}</span>
                {renderStatus(latest.rsi_7 > 50 ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Stochastic (%K, %D)</span>
                <span className="ind-val">%K: {latest.stoch_k?.toFixed(1)} | %D: {latest.stoch_d?.toFixed(1)}</span>
                {renderStatus(latest.stoch_k > latest.stoch_d ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Stochastic RSI</span>
                <span className="ind-val">%K: {latest.stoch_rsi_k?.toFixed(1)} | %D: {latest.stoch_rsi_d?.toFixed(1)}</span>
                {renderStatus(latest.stoch_rsi_k > 80 ? "bearish" : latest.stoch_rsi_k < 20 ? "bullish" : "neutral")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Money Flow Index (MFI 14)</span>
                <span className="ind-val">{latest.mfi_14?.toFixed(1)}</span>
                {renderStatus(latest.mfi_14 > 50 ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Williams %R (14)</span>
                <span className="ind-val">{latest.williams_r?.toFixed(1)}</span>
                {renderStatus(latest.williams_r > -20 ? "bearish" : latest.williams_r < -80 ? "bullish" : "neutral")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Ultimate Oscillator (7, 14, 28)</span>
                <span className="ind-val">{latest.ultimate_oscillator?.toFixed(1)}</span>
                {renderStatus(latest.ultimate_oscillator > 50 ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Rate of Change (ROC 12)</span>
                <span className="ind-val">{latest.roc_12?.toFixed(2)}%</span>
                {renderStatus(latest.roc_12 > 0 ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">RSI Divergence</span>
                <span className="ind-val">
                  {latest.bullish_divergence ? "Bullish Divergence Detected" : latest.bearish_divergence ? "Bearish Divergence Detected" : "No divergence"}
                </span>
                {renderStatus(latest.bullish_divergence ? "bullish" : latest.bearish_divergence ? "bearish" : "neutral")}
              </div>
            </div>
          </div>
        )}

        {/* 3. VOLATILITY & BANDS */}
        {(activeCategory === "all" || activeCategory === "volatility") && (
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Activity size={14} style={{ color: "#00E676" }} /> 3. Volatility & Channel Envelopes
              </span>
            </div>
            <div className="indicator-list">
              <div className="indicator-row">
                <span className="ind-name">Bollinger Bands (20, 2)</span>
                <span className="ind-val">U: ${latest.bb_upper?.toFixed(2)} | L: ${latest.bb_lower?.toFixed(2)}</span>
                {renderStatus(currentPrice > latest.bb_middle ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Bollinger Bandwidth & Squeeze</span>
                <span className="ind-val">Width: {latest.bb_bandwidth?.toFixed(2)}%</span>
                {renderStatus(latest.bb_squeeze ? "bearish" : "neutral", latest.bb_squeeze ? "SQUEEZE ACTIVE" : "NORMAL")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Average True Range (ATR 14)</span>
                <span className="ind-val">${latest.atr_14?.toFixed(4)} ({latest.natr_14?.toFixed(2)}%)</span>
                {renderStatus(latest.natr_14 > 3 ? "bearish" : "neutral", latest.natr_14 > 3 ? "HIGH VOLATILITY" : "MODERATE")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Keltner Channels (20, 1.5)</span>
                <span className="ind-val">U: ${latest.kc_upper?.toFixed(2)} | L: ${latest.kc_lower?.toFixed(2)}</span>
                {renderStatus(currentPrice > latest.kc_middle ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Donchian Channels (20)</span>
                <span className="ind-val">High: ${latest.dc_upper?.toFixed(2)} | Low: ${latest.dc_lower?.toFixed(2)}</span>
                {renderStatus(currentPrice >= latest.dc_upper ? "bullish" : currentPrice <= latest.dc_lower ? "bearish" : "neutral")}
              </div>
            </div>
          </div>
        )}

        {/* 4. VOLUME & LIQUIDITY */}
        {(activeCategory === "all" || activeCategory === "volume") && (
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <BarChart2 size={14} style={{ color: "#00B0FF" }} /> 4. Volume Profile & Liquidity Analysis
              </span>
            </div>
            <div className="indicator-list">
              <div className="indicator-row">
                <span className="ind-name">Volume Weighted Avg Price (VWAP)</span>
                <span className="ind-val">${latest.vwap?.toFixed(2)}</span>
                {renderStatus(currentPrice > latest.vwap ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">VWAP Upper / Lower (+1σ, -1σ)</span>
                <span className="ind-val">${latest.vwap_upper_1?.toFixed(2)} / ${latest.vwap_lower_1?.toFixed(2)}</span>
                {renderStatus(currentPrice > latest.vwap ? "bullish" : "bearish")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Volume Profile Point of Control (POC)</span>
                <span className="ind-val">${vp.poc?.toFixed(2)}</span>
                {renderStatus(currentPrice > vp.poc ? "bullish" : "bearish", "HIGH VOLUME NODE")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Value Area High (VAH) / Low (VAL)</span>
                <span className="ind-val">VAH: ${vp.vah?.toFixed(2)} | VAL: ${vp.val?.toFixed(2)}</span>
                {renderStatus(currentPrice > vp.vah ? "bullish" : currentPrice < vp.val ? "bearish" : "neutral")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Chaikin Money Flow (CMF 20)</span>
                <span className="ind-val">{latest.cmf_20?.toFixed(3)}</span>
                {renderStatus(latest.cmf_20 > 0.05 ? "bullish" : latest.cmf_20 < -0.05 ? "bearish" : "neutral")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">On-Balance Volume (OBV)</span>
                <span className="ind-val">{latest.obv?.toLocaleString()}</span>
                {renderStatus("neutral", "FLOW TRACKER")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Volume Spike Alert</span>
                <span className="ind-val">{latest.vol_spike ? "Volume > 2x 20SMA" : "Normal Volume Flow"}</span>
                {renderStatus(latest.vol_spike ? "bullish" : "neutral", latest.vol_spike ? "SPIKE DETECTED" : "NORMAL")}
              </div>
            </div>
          </div>
        )}

        {/* 5. SMART MONEY CONCEPTS (SMC) & PIVOTS */}
        {(activeCategory === "all" || activeCategory === "smc") && (
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Compass size={14} style={{ color: "#E040FB" }} /> 5. Institutional Structure (SMC) & Pivots
              </span>
            </div>
            <div className="indicator-list">
              <div className="indicator-row">
                <span className="ind-name">Order Blocks (OB)</span>
                <span className="ind-val">{smc.order_blocks?.length || 0} active zones</span>
                {renderStatus(smc.order_blocks?.some((ob: any) => !ob.mitigated && ob.type === "bullish") ? "bullish" : "neutral", "RESTING LIQUIDITY")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Fair Value Gaps (FVG)</span>
                <span className="ind-val">{smc.fvgs?.length || 0} imbalance gaps</span>
                {renderStatus("neutral", "PRICE MAGNETS")}
              </div>
              <div className="indicator-row">
                <span className="ind-name">Breaks of Structure (BoS)</span>
                <span className="ind-val">{smc.bos?.length || 0} structural shifts</span>
                {renderStatus(smc.bos?.length > 0 ? "bullish" : "neutral")}
              </div>
              {pivots.standard && (
                <>
                  <div className="indicator-row">
                    <span className="ind-name">Daily Pivot Point (PP)</span>
                    <span className="ind-val">${pivots.standard.pivot}</span>
                    {renderStatus(currentPrice > pivots.standard.pivot ? "bullish" : "bearish")}
                  </div>
                  <div className="indicator-row">
                    <span className="ind-name">Resistance R1 / Support S1</span>
                    <span className="ind-val">R1: ${pivots.standard.r1} | S1: ${pivots.standard.s1}</span>
                    {renderStatus("neutral", "KEY ROADMAP")}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* 6. CANDLESTICK PATTERNS */}
        {(activeCategory === "all" || activeCategory === "patterns") && (
          <div className="tv-panel">
            <div className="tv-panel-header">
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Gauge size={14} style={{ color: "#FF9100" }} /> 6. Candlestick Patterns Detected
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", padding: "8px 0" }}>
              {[
                { name: "Bullish Engulfing", active: patterns.bullish_engulfing, type: "bullish" },
                { name: "Bearish Engulfing", active: patterns.bearish_engulfing, type: "bearish" },
                { name: "Hammer", active: patterns.hammer, type: "bullish" },
                { name: "Shooting Star", active: patterns.shooting_star, type: "bearish" },
                { name: "Morning Star", active: patterns.morning_star, type: "bullish" },
                { name: "Evening Star", active: patterns.evening_star, type: "bearish" },
                { name: "Three White Soldiers", active: patterns.three_white_soldiers, type: "bullish" },
                { name: "Three Black Crows", active: patterns.three_black_crows, type: "bearish" },
                { name: "Harami", active: patterns.harami, type: "neutral" },
                { name: "Doji", active: patterns.doji, type: "neutral" },
              ].map((p, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "8px",
                    borderRadius: "4px",
                    backgroundColor: p.active ? (p.type === "bullish" ? "rgba(8, 153, 129, 0.15)" : p.type === "bearish" ? "rgba(242, 54, 69, 0.15)" : "rgba(255, 152, 0, 0.15)") : "#1e222d",
                    border: `1px solid ${p.active ? (p.type === "bullish" ? "#089981" : p.type === "bearish" ? "#f23645" : "#FF9800") : "#2a2e39"}`,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center"
                  }}
                >
                  <span style={{ fontSize: "11px", color: p.active ? "#fff" : "#787b86", fontWeight: p.active ? 600 : 400 }}>
                    {p.name}
                  </span>
                  {p.active ? (
                    <span style={{ fontSize: "10px", fontWeight: "bold", color: p.type === "bullish" ? "#089981" : p.type === "bearish" ? "#f23645" : "#FF9800" }}>
                      ACTIVE
                    </span>
                  ) : (
                    <span style={{ fontSize: "10px", color: "#50535e" }}>-</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

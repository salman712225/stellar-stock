import React from "react";

interface ConsensusGaugeProps {
  value: number; // 0 to 100
  label: string; // e.g., "STRONG BUY", "NEUTRAL", etc.
  color: string; // hex color code
}

export const ConsensusGauge: React.FC<ConsensusGaugeProps> = ({ value, label, color }) => {
  // Map value (0-100) to degrees (-90 to 90) for speedometer needle rotation
  const needleRotation = (value / 100) * 180 - 90;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%", padding: "10px 0" }}>
      <div style={{ position: "relative", width: "200px", height: "110px", overflow: "hidden" }}>
        {/* Speedometer semi-circle outline SVG */}
        <svg width="200" height="110" viewBox="0 0 200 110">
          {/* Background Arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#1c2030"
            strokeWidth="14"
            strokeLinecap="round"
          />
          {/* Strong Sell Segment */}
          <path
            d="M 20 100 A 80 80 0 0 1 68 45"
            fill="none"
            stroke="rgba(242, 54, 69, 0.25)"
            strokeWidth="14"
          />
          {/* Sell/Neutral Segment */}
          <path
            d="M 68 45 A 80 80 0 0 1 132 45"
            fill="none"
            stroke="rgba(120, 123, 134, 0.2)"
            strokeWidth="14"
          />
          {/* Buy Segment */}
          <path
            d="M 132 45 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="rgba(8, 153, 129, 0.25)"
            strokeWidth="14"
          />
          
          {/* Active colored bar overlay */}
          <path
            d={`M 20 100 A 80 80 0 0 1 ${20 + (value/100)*160} ${100 - Math.sin((value/100) * Math.PI) * 80}`}
            fill="none"
            stroke={color}
            strokeWidth="14"
            strokeLinecap="round"
            style={{ opacity: 0.15, display: value > 0 ? "block" : "none" }}
          />

          {/* Center Hub */}
          <circle cx="100" cy="100" r="8" fill="#787b86" />
          <circle cx="100" cy="100" r="4" fill="#0c0d14" />
        </svg>

        {/* Speedometer Needle */}
        <div
          style={{
            position: "absolute",
            bottom: "10px",
            left: "calc(50% - 2px)",
            width: "4px",
            height: "80px",
            background: `linear-gradient(to top, #787b86 0%, ${color} 100%)`,
            borderRadius: "4px",
            transformOrigin: "bottom center",
            transform: `rotate(${needleRotation}deg)`,
            transition: "transform 0.5s cubic-bezier(0.1, 0.8, 0.2, 1)",
            boxShadow: `0 0 8px ${color}4d`,
          }}
        />
      </div>

      {/* Text indicators */}
      <div style={{ textAlign: "center", marginTop: "-5px" }}>
        <div style={{ color: color, fontSize: "14px", fontWeight: 700, letterSpacing: "0.5px" }}>
          {label}
        </div>
        <div style={{ color: "#787b86", fontSize: "10px", marginTop: "2px" }}>
          Consensus Meter: {Math.round(value)}/100
        </div>
      </div>
    </div>
  );
};

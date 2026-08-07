import React from "react";

interface AddPositionFormProps {
  formSymbol: string;
  setFormSymbol: (v: string) => void;
  formType: "long" | "short" | "call" | "put";
  setFormType: (v: "long" | "short" | "call" | "put") => void;
  formStrike: string;
  setFormStrike: (v: string) => void;
  formEntry: string;
  setFormEntry: (v: string) => void;
  formLimit: string;
  setFormLimit: (v: string) => void;
  formSl: string;
  setFormSl: (v: string) => void;
  formTf: string;
  setFormTf: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export const AddPositionForm: React.FC<AddPositionFormProps> = ({
  formSymbol,
  setFormSymbol,
  formType,
  setFormType,
  formStrike,
  setFormStrike,
  formEntry,
  setFormEntry,
  formLimit,
  setFormLimit,
  formSl,
  setFormSl,
  formTf,
  setFormTf,
  onSubmit,
}) => {
  return (
    <div className="tv-panel">
      <div className="tv-panel-header">
        <span>➕ Track New Position</span>
      </div>

      <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
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
          <label>Position Type</label>
          <select
            className="form-select"
            value={formType}
            onChange={(e) => setFormType(e.target.value as any)}
          >
            <option value="long">Long</option>
            <option value="short">Short</option>
            <option value="call">Call Option</option>
            <option value="put">Put Option</option>
          </select>
        </div>

        {(formType === "call" || formType === "put") && (
          <div className="form-group">
            <label>Strike Price ($)</label>
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
          <label>Entry Price ($)</label>
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
          <select className="form-select" value={formTf} onChange={(e) => setFormTf(e.target.value)}>
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
  );
};

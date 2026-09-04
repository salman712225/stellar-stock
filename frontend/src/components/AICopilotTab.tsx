import React, { useState } from "react";
import { Sparkles, Send, Bot, User, Copy, Check, Award } from "lucide-react";
import { API_URL } from "../config";

interface AICopilotTabProps {
  analysisData: any;
  activeSymbol: string;
}

interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  text: string;
  time: string;
}

export const AICopilotTab: React.FC<AICopilotTabProps> = ({ analysisData, activeSymbol }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      sender: "ai",
      text: `Hello! I am your institutional **AI Strategy Copilot**. I have parsed the real-time order books, technical indicators, SMC structures, and news sentiment for **${activeSymbol}**. What would you like to analyze?`,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    }
  ]);
  const [inputVal, setInputVal] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [copied, setCopied] = useState(false);

  const quickPrompts = [
    `What is the ideal entry setup for ${activeSymbol}?`,
    `What are the key Support & Resistance pivot zones?`,
    `Explain the SMC Order Block & Fair Value Gaps`,
    `What is the current risk-reward ratio and stop loss?`
  ];

  const handleSendMessage = async (customPrompt?: string) => {
    const textToSend = customPrompt || inputVal;
    if (!textToSend.trim() || isSending) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: "user",
      text: textToSend,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customPrompt) setInputVal("");
    setIsSending(true);

    try {
      const res = await fetch(`${API_URL}/api/ai-copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: activeSymbol,
          question: textToSend,
          context: analysisData
        })
      });

      if (res.ok) {
        const data = await res.json();
        const aiMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          sender: "ai",
          text: data.answer || "No response received from AI model.",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        };
        setMessages((prev) => [...prev, aiMsg]);
      } else {
        throw new Error("Failed to get response");
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "ai",
        text: `⚠️ **Error connecting to AI Copilot**: ${err.message || "Please check backend server."}`,
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleCopyReport = () => {
    if (analysisData?.report) {
      navigator.clipboard.writeText(analysisData.report);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "16px", height: "calc(100vh - 170px)", minHeight: "600px" }}>
      {/* LEFT COLUMN: Institutional Trade Dossier */}
      <div className="tv-panel" style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
        <div className="tv-panel-header" style={{ flexShrink: 0 }}>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Award size={14} style={{ color: "#2962ff" }} /> Institutional Research Dossier
          </span>
          <button
            className="btn-secondary"
            onClick={handleCopyReport}
            style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", padding: "3px 8px" }}
          >
            {copied ? <Check size={11} style={{ color: "#089981" }} /> : <Copy size={11} />}
            {copied ? "Copied!" : "Copy Report"}
          </button>
        </div>

        <div
          className="report-markdown"
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "16px",
            backgroundColor: "#131722",
            borderRadius: "4px"
          }}
        >
          {analysisData?.report ? (
            <div
              dangerouslySetInnerHTML={{
                __html: analysisData.report
                  .replace(/^# (.*$)/gim, '<h2 style="color:#2962ff; margin-top:0;">$1</h2>')
                  .replace(/^## (.*$)/gim, '<h3 style="color:#d1d4dc; border-bottom:1px solid #2a2e39; padding-bottom:4px; margin-top:16px;">$1</h3>')
                  .replace(/^### (.*$)/gim, '<h4 style="color:#90caf9; margin-top:12px;">$1</h4>')
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/`(.*?)`/g, '<code style="background:#1e222d; padding:2px 4px; border-radius:3px; color:#FFCA28;">$1</code>')
                  .replace(/\n/g, '<br/>')
              }}
            />
          ) : (
            <div style={{ textAlign: "center", color: "#787b86", padding: "60px 0" }}>
              Generating full quantitative dossier...
            </div>
          )}
        </div>
      </div>

      {/* RIGHT COLUMN: Interactive Strategy Copilot */}
      <div className="tv-panel" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <div className="tv-panel-header" style={{ flexShrink: 0 }}>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Bot size={15} style={{ color: "#00E676" }} /> AI Strategy Copilot
          </span>
          <span style={{ fontSize: "10px", color: "#089981", display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "#089981" }} /> Online
          </span>
        </div>

        {/* Chat Message Stream */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "12px",
            display: "flex",
            flexDirection: "column",
            gap: "12px"
          }}
        >
          {messages.map((m) => (
            <div
              key={m.id}
              style={{
                display: "flex",
                gap: "8px",
                alignItems: "flex-start",
                alignSelf: m.sender === "user" ? "flex-end" : "flex-start",
                maxWidth: "88%"
              }}
            >
              {m.sender === "ai" && (
                <div
                  style={{
                    width: "26px",
                    height: "26px",
                    borderRadius: "50%",
                    backgroundColor: "#2962ff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0
                  }}
                >
                  <Bot size={14} color="#fff" />
                </div>
              )}

              <div
                style={{
                  backgroundColor: m.sender === "user" ? "#2962ff" : "#1e222d",
                  color: "#d1d4dc",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  fontSize: "12px",
                  lineHeight: "1.5",
                  border: m.sender === "ai" ? "1px solid #2a2e39" : "none"
                }}
              >
                <div
                  dangerouslySetInnerHTML={{
                    __html: m.text
                      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                      .replace(/`(.*?)`/g, '<code style="background:#131722; padding:1px 3px; border-radius:3px; color:#FFCA28;">$1</code>')
                      .replace(/\n/g, '<br/>')
                  }}
                />
                <div style={{ fontSize: "9px", color: m.sender === "user" ? "#bbdefb" : "#787b86", textAlign: "right", marginTop: "4px" }}>
                  {m.time}
                </div>
              </div>

              {m.sender === "user" && (
                <div
                  style={{
                    width: "26px",
                    height: "26px",
                    borderRadius: "50%",
                    backgroundColor: "#FF9800",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0
                  }}
                >
                  <User size={14} color="#fff" />
                </div>
              )}
            </div>
          ))}

          {isSending && (
            <div style={{ display: "flex", gap: "8px", alignItems: "center", color: "#787b86", fontSize: "11px" }}>
              <Sparkles size={13} className="spin" style={{ color: "#2962ff" }} /> Copilot calculating strategy & levels...
            </div>
          )}
        </div>

        {/* Quick Suggestion Chips */}
        <div style={{ padding: "8px 12px", borderTop: "1px solid #2a2e39", display: "flex", gap: "6px", overflowX: "auto", flexShrink: 0 }}>
          {quickPrompts.map((p, idx) => (
            <button
              key={idx}
              className="btn-secondary"
              onClick={() => handleSendMessage(p)}
              disabled={isSending}
              style={{ fontSize: "10px", padding: "3px 8px", whiteSpace: "nowrap" }}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Chat Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          style={{ display: "flex", gap: "8px", padding: "10px 12px", borderTop: "1px solid #2a2e39", flexShrink: 0 }}
        >
          <input
            type="text"
            className="form-input"
            placeholder={`Ask AI Copilot about ${activeSymbol}...`}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            disabled={isSending}
            style={{ fontSize: "12px" }}
          />
          <button type="submit" className="btn-primary" disabled={isSending || !inputVal.trim()} style={{ width: "auto", padding: "0 14px" }}>
            <Send size={13} />
          </button>
        </form>
      </div>
    </div>
  );
};

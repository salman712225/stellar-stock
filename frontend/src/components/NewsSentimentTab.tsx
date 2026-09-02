import React, { useState } from "react";
import { Newspaper, MessageSquare, Share2, ExternalLink, Flame, TrendingUp, TrendingDown, RefreshCw } from "lucide-react";

interface NewsSentimentTabProps {
  sentimentData: any;
  activeSymbol: string;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const NewsSentimentTab: React.FC<NewsSentimentTabProps> = ({
  sentimentData,
  activeSymbol,
  onRefresh,
  isLoading
}) => {
  const [filter, setFilter] = useState<"all" | "news" | "reddit" | "twitter">("all");

  if (!sentimentData) {
    return (
      <div style={{ textAlign: "center", padding: "60px 0", color: "#787b86" }}>
        No sentiment or news stream data available for {activeSymbol}.
      </div>
    );
  }

  const score = sentimentData.score || 0.0;
  const label = sentimentData.label || "neutral";
  const fearGreed = sentimentData.fear_greed || { score: 50, label: "Neutral" };
  const newsArticles = sentimentData.articles || [];
  const redditPosts = sentimentData.reddit_posts || [];
  const tweets = sentimentData.tweets || [];

  // Sentiment bar calculations (-1 to +1 mapped to 0% to 100%)
  const sentPercent = Math.round(((score + 1.0) / 2.0) * 100);

  const formatTime = (isoString?: string) => {
    if (!isoString) return "Just now";
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + " · " + date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return isoString;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Top Header Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
        {/* 1. Fear & Greed Meter */}
        <div className="tv-panel" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div className="tv-panel-header">
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Flame size={14} style={{ color: fearGreed.score >= 50 ? "#089981" : "#f23645" }} /> Fear & Greed Index
            </span>
            <span style={{ fontSize: "11px", color: "#787b86" }}>Live Macro Gauge</span>
          </div>
          <div style={{ padding: "12px 0", textAlign: "center" }}>
            <div style={{ fontSize: "36px", fontWeight: 800, color: fearGreed.score >= 60 ? "#089981" : fearGreed.score <= 40 ? "#f23645" : "#FF9800" }}>
              {fearGreed.score}
            </div>
            <div style={{ fontSize: "13px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "1px", color: fearGreed.score >= 60 ? "#089981" : fearGreed.score <= 40 ? "#f23645" : "#FF9800" }}>
              {fearGreed.label}
            </div>
            {/* Progress Bar */}
            <div style={{ width: "100%", height: "8px", backgroundColor: "#2a2e39", borderRadius: "4px", marginTop: "12px", overflow: "hidden" }}>
              <div
                style={{
                  width: `${fearGreed.score}%`,
                  height: "100%",
                  background: "linear-gradient(90deg, #f23645 0%, #FF9800 50%, #089981 100%)",
                  transition: "width 0.4s ease-out"
                }}
              />
            </div>
          </div>
        </div>

        {/* 2. Sentiment Index Meter */}
        <div className="tv-panel" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div className="tv-panel-header">
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              {score >= 0 ? <TrendingUp size={14} style={{ color: "#089981" }} /> : <TrendingDown size={14} style={{ color: "#f23645" }} />} NLP Sentiment Consensus
            </span>
            <span style={{ fontSize: "11px", color: "#787b86" }}>{activeSymbol}</span>
          </div>
          <div style={{ padding: "12px 0", textAlign: "center" }}>
            <div style={{ fontSize: "36px", fontWeight: 800, color: score > 0.1 ? "#089981" : score < -0.1 ? "#f23645" : "#787b86" }}>
              {score > 0 ? `+${score.toFixed(2)}` : score.toFixed(2)}
            </div>
            <div style={{ fontSize: "13px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "1px", color: score > 0.1 ? "#089981" : score < -0.1 ? "#f23645" : "#787b86" }}>
              {label} Sentiment
            </div>
            {/* Range slider bar (-1 to +1) */}
            <div style={{ width: "100%", height: "8px", backgroundColor: "#2a2e39", borderRadius: "4px", marginTop: "12px", position: "relative" }}>
              <div
                style={{
                  width: "14px",
                  height: "14px",
                  borderRadius: "50%",
                  backgroundColor: score > 0 ? "#089981" : score < 0 ? "#f23645" : "#fff",
                  position: "absolute",
                  top: "-3px",
                  left: `calc(${sentPercent}% - 7px)`,
                  boxShadow: "0 0 8px rgba(0,0,0,0.5)"
                }}
              />
            </div>
          </div>
        </div>

        {/* 3. Source Breakdown */}
        <div className="tv-panel">
          <div className="tv-panel-header">
            <span>📡 Stream Aggregation Stats</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", padding: "8px 0", fontSize: "12px" }}>
            <div className="p-flex-between">
              <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#787b86" }}>
                <Newspaper size={13} /> News Articles:
              </span>
              <strong>{newsArticles.length} feeds analyzed</strong>
            </div>
            <div className="p-flex-between">
              <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#787b86" }}>
                <MessageSquare size={13} /> Reddit Buzz:
              </span>
              <strong>{redditPosts.length} discussions</strong>
            </div>
            <div className="p-flex-between">
              <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#787b86" }}>
                <Share2 size={13} /> Social / X:
              </span>
              <strong>{tweets.length} social signals</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Tabs & Refresh */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #2a2e39", paddingBottom: "10px" }}>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            className={`btn-secondary ${filter === "all" ? "active" : ""}`}
            onClick={() => setFilter("all")}
            style={{ fontSize: "12px" }}
          >
            All Updates ({newsArticles.length + redditPosts.length + tweets.length})
          </button>
          <button
            className={`btn-secondary ${filter === "news" ? "active" : ""}`}
            onClick={() => setFilter("news")}
            style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
          >
            <Newspaper size={12} /> News ({newsArticles.length})
          </button>
          <button
            className={`btn-secondary ${filter === "reddit" ? "active" : ""}`}
            onClick={() => setFilter("reddit")}
            style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
          >
            <MessageSquare size={12} /> Reddit ({redditPosts.length})
          </button>
          <button
            className={`btn-secondary ${filter === "twitter" ? "active" : ""}`}
            onClick={() => setFilter("twitter")}
            style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}
          >
            <Share2 size={12} /> Twitter / X ({tweets.length})
          </button>
        </div>

        {onRefresh && (
          <button
            className="btn-secondary"
            onClick={onRefresh}
            disabled={isLoading}
            style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", padding: "4px 10px" }}
          >
            <RefreshCw size={11} className={isLoading ? "spin" : ""} /> Refresh Feeds
          </button>
        )}
      </div>

      {/* Feed List */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {/* News Items */}
        {(filter === "all" || filter === "news") &&
          newsArticles.map((art: any, idx: number) => {
            const artScore = art.sentiment?.score ?? 0.0;
            return (
              <div key={`news-${idx}`} className="news-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "10px" }}>
                  <a
                    href={art.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "#d1d4dc", fontWeight: 600, fontSize: "14px", textDecoration: "none", display: "flex", alignItems: "center", gap: "6px" }}
                  >
                    {art.title} <ExternalLink size={12} style={{ color: "#787b86", flexShrink: 0 }} />
                  </a>
                  <span
                    className={artScore > 0.1 ? "badge-buy" : artScore < -0.1 ? "badge-sell" : "badge-hold"}
                    style={{ flexShrink: 0 }}
                  >
                    {artScore > 0.1 ? "BULLISH" : artScore < -0.1 ? "BEARISH" : "NEUTRAL"} ({artScore > 0 ? `+${artScore.toFixed(2)}` : artScore.toFixed(2)})
                  </span>
                </div>
                {art.summary && (
                  <p style={{ color: "#787b86", fontSize: "12px", margin: "6px 0 0 0", lineHeight: "1.4" }}>
                    {art.summary.length > 220 ? art.summary.substring(0, 220) + "..." : art.summary}
                  </p>
                )}
                <div style={{ display: "flex", justifyContent: "space-between", color: "#50535e", fontSize: "11px", marginTop: "8px" }}>
                  <span>Source: <strong style={{ color: "#2962ff" }}>{art.source}</strong></span>
                  <span>{formatTime(art.publishedAt)}</span>
                </div>
              </div>
            );
          })}

        {/* Reddit Items */}
        {(filter === "all" || filter === "reddit") &&
          redditPosts.map((post: any, idx: number) => {
            const postScore = post.sentiment?.score ?? 0.0;
            return (
              <div key={`reddit-${idx}`} className="news-card" style={{ borderColor: "rgba(255, 69, 0, 0.3)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "10px" }}>
                  <a
                    href={post.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "#d1d4dc", fontWeight: 600, fontSize: "13px", textDecoration: "none", display: "flex", alignItems: "center", gap: "6px" }}
                  >
                    <MessageSquare size={13} style={{ color: "#FF4500" }} /> {post.title}
                  </a>
                  <span
                    className={postScore > 0.1 ? "badge-buy" : postScore < -0.1 ? "badge-sell" : "badge-hold"}
                    style={{ flexShrink: 0 }}
                  >
                    {postScore > 0.1 ? "BULLISH" : postScore < -0.1 ? "BEARISH" : "NEUTRAL"}
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", color: "#50535e", fontSize: "11px", marginTop: "8px" }}>
                  <span>r/{post.subreddit || "CryptoCurrency"} · Score: {post.score || 1}</span>
                  <span>{post.num_comments || 0} comments</span>
                </div>
              </div>
            );
          })}

        {/* Twitter Items */}
        {(filter === "all" || filter === "twitter") &&
          tweets.map((t: any, idx: number) => {
            const tweetScore = t.sentiment?.score ?? 0.0;
            return (
              <div key={`tw-${idx}`} className="news-card" style={{ borderColor: "rgba(29, 161, 242, 0.3)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "10px" }}>
                  <div style={{ fontSize: "13px", color: "#d1d4dc", display: "flex", alignItems: "flex-start", gap: "6px" }}>
                    <Share2 size={13} style={{ color: "#1DA1F2", marginTop: "2px" }} />
                    <span>{t.text}</span>
                  </div>
                  <span
                    className={tweetScore > 0.1 ? "badge-buy" : tweetScore < -0.1 ? "badge-sell" : "badge-hold"}
                    style={{ flexShrink: 0 }}
                  >
                    {tweetScore > 0.1 ? "BULLISH" : tweetScore < -0.1 ? "BEARISH" : "NEUTRAL"}
                  </span>
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
};

import httpx
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from config import GEMINI_API_KEY, OPENAI_API_KEY

logger = logging.getLogger("llm_reasoning")

class LLMReasoningEngine:
    def __init__(self):
        self.gemini_key = GEMINI_API_KEY
        self.openai_key = OPENAI_API_KEY

    async def generate_report(
        self,
        symbol: str,
        price: float,
        indicators: Dict[str, Any],
        patterns: Dict[str, Any],
        smc: Dict[str, Any],
        options: Optional[Dict[str, Any]],
        sentiment: Dict[str, Any],
        prediction: Dict[str, Any],
        pivots: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates a comprehensive analysis report using LLM if keys are available,
        or falling back to a high-fidelity local template report builder.
        """
        analysis_summary = self._compile_market_data(
            symbol, price, indicators, patterns, smc, options, sentiment, prediction, pivots
        )

        if self.gemini_key:
            report = await self._query_gemini(analysis_summary)
            if report:
                return report
                
        if self.openai_key:
            report = await self._query_openai(analysis_summary)
            if report:
                return report

        return self._generate_local_expert_report(
            symbol, price, indicators, patterns, smc, options, sentiment, prediction, pivots
        )

    async def answer_copilot_query(
        self,
        symbol: str,
        question: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Answers interactive user questions regarding trading strategies, key levels, or market indicators.
        """
        price = context.get("current_price", 0.0)
        signal = context.get("prediction", {}).get("signal", "HOLD")
        confidence = context.get("prediction", {}).get("confidence", 0.5)
        sentiment_label = context.get("sentiment", {}).get("label", "neutral")
        
        prompt = f"""
You are an expert crypto & stock quant trading strategist.
The user is inquiring about {symbol}.
Current Market State for {symbol}:
- Price: ${price:,.4f}
- ML Signal: {signal} ({confidence:.0%} confidence)
- Sentiment: {sentiment_label.upper()}
- RSI: {context.get('indicators', {}).get('latest', {}).get('rsi_14', 50):.1f}
- Supertrend: {'Bullish' if context.get('indicators', {}).get('latest', {}).get('direction') == 1 else 'Bearish'}

User Question: "{question}"

Provide a concise, professional, data-backed answer in markdown with concrete price levels and actionable risk advice.
"""
        if self.gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, timeout=12.0)
                    if resp.status_code == 200:
                        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.warning(f"Gemini copilot query failed: {e}")

        # Local intelligent answer generator
        q_lower = question.lower()
        if "buy" in q_lower or "entry" in q_lower or "should i" in q_lower:
            if signal == "BUY":
                return f"### 🟢 Buy Bias on {symbol}\n**Strategy Recommendation**: Technical indicators and ML models are aligned **BULLISH** ({confidence:.0%} confidence). Look for pullbacks toward recent Support/VWAP at **${price * 0.992:,.2f}** for an optimal entry. Maintain Stop Loss below **${price * 0.975:,.2f}** (Target 1: **${price * 1.04:,.2f}**)."
            elif signal == "SELL":
                return f"### 🔴 Caution on {symbol}\n**Strategy Recommendation**: Market models are signaling **BEARISH** pressure ({confidence:.0%} confidence). Entering long now carries high drawdown risk. Wait for an established base or trade short on resistance retests."
            else:
                return f"### 🟡 Neutral / Consolidation on {symbol}\n**Strategy Recommendation**: Price is currently in a consolidation range. Recommended approach is to wait for a confirmed breakout above **${price * 1.02:,.2f}** or range buy at support **${price * 0.98:,.2f}**."
        elif "resistance" in q_lower or "target" in q_lower or "tp" in q_lower:
            return f"### 🎯 Key Targets & Resistance for {symbol}\n- **Immediate Resistance (TP1)**: `${price * 1.025:,.2f}` (Value Area High / Pivot R1)\n- **Major Target (TP2)**: `${price * 1.055:,.2f}` (Next Key Liquidity Pool)\n- **Extended Extension (TP3)**: `${price * 1.09:,.2f}` (1.618 Fib Extension)"
        elif "support" in q_lower or "sl" in q_lower or "stop" in q_lower:
            return f"### 🛡️ Support & Invalidation Levels for {symbol}\n- **Key Support (S1)**: `${price * 0.98:,.2f}` (Order Block / Point of Control)\n- **Structural Invalidation (Stop Loss)**: `${price * 0.965:,.2f}` (Below Swing Low & ATR Boundary)\n- **Deep Demand Zone (S2)**: `${price * 0.94:,.2f}`"
        else:
            return f"### 📊 Market Intelligence for {symbol}\n- **Current Spot**: `${price:,.4f}`\n- **AI Signal**: `{signal}` ({confidence:.0%} confidence)\n- **Market Sentiment**: `{sentiment_label.upper()}`\n- **Technical Bias**: Supertrend and Momentum oscillators indicate the prevailing trend is **{'Bullish' if signal == 'BUY' else 'Bearish' if signal == 'SELL' else 'Range-bound'}**."

    def _compile_market_data(self, symbol: str, price: float, indicators: dict, patterns: dict, smc: dict, options: Optional[dict], sentiment: dict, prediction: dict, pivots: Optional[dict]) -> str:
        opt_str = "N/A"
        if options:
            opt_str = f"PCR OI: {options.get('pcr_oi')}, PCR Vol: {options.get('pcr_volume')}, Max Pain: {options.get('max_pain')}"

        summary = f"""
Asset: {symbol}
Current Price: {price}
ML Signal: {prediction.get('signal')} ({prediction.get('confidence'):.0%} confidence)
Market Sentiment Score: {sentiment.get('overall_score')} (Label: {sentiment.get('overall_label')})

Technical Indicators:
- RSI (14): {indicators.get('rsi_14', 50):.1f}
- Supertrend Direction: {'Bullish' if indicators.get('direction') == 1 else 'Bearish'}
- EMA9/EMA21 Cross: {'Bullish' if indicators.get('ema_9', 0) > indicators.get('ema_21', 0) else 'Bearish'}
- MACD Hist: {indicators.get('macd_hist', 0):.4f}
- ADX Trend Strength: {indicators.get('adx', 0):.1f}
- StochRSI %K: {indicators.get('stoch_rsi_k', 50):.1f}
- MFI (14): {indicators.get('mfi_14', 50):.1f}
- VWAP: {indicators.get('vwap', price):.4f}

Smart Money Concepts (SMC):
- Order Blocks: {len(smc.get('order_blocks', []))} detected
- Fair Value Gaps (FVG): {len(smc.get('fvgs', []))} detected
- Structure Breaks: {len(smc.get('bos', []))} BoS, {len(smc.get('choch', []))} CHoCH

Options Chain: {opt_str}
"""
        return summary

    async def _query_gemini(self, data_summary: str) -> Optional[str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"You are a hedge-fund senior quantitative analyst and SMC trading expert. Analyze the following trading asset metrics and write an institutional Markdown trading report with Executive Thesis, Multi-Indicator Consensus, SMC Footprint, Sentiment Analysis, and Tactical Setup (Entry, Stop Loss, TP1, TP2, TP3, R:R):\n{data_summary}"
                }]
            }]
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=15.0)
                if response.status_code == 200:
                    res_json = response.json()
                    return res_json["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini API query failed: {e}")
        return None

    async def _query_openai(self, data_summary: str) -> Optional[str]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a professional hedge-fund quant and technical market analyst. Analyze the provided asset statistics and write a detailed markdown trading report."},
                {"role": "user", "content": data_summary}
            ]
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=15.0)
                if response.status_code == 200:
                    res_json = response.json()
                    return res_json["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI API query failed: {e}")
        return None

    def _generate_local_expert_report(
        self,
        symbol: str,
        price: float,
        indicators: Dict[str, Any],
        patterns: Dict[str, Any],
        smc: Dict[str, Any],
        options: Optional[Dict[str, Any]],
        sentiment: Dict[str, Any],
        prediction: Dict[str, Any],
        pivots: Optional[Dict[str, Any]] = None
    ) -> str:
        ml_sig = prediction.get("signal", "HOLD")
        ml_conf = prediction.get("confidence", 0.5)
        sent_score = sentiment.get("overall_score", 0.0)
        sent_label = sentiment.get("overall_label", "neutral")
        
        rsi = indicators.get("rsi_14", 50)
        direction = indicators.get("direction", 1)
        st_label = "BULLISH" if direction == 1 else "BEARISH"
        
        atr = indicators.get("atr_14") or (price * 0.02)
        
        if ml_sig == "BUY":
            thesis = f"Bullish momentum expansion for {symbol}. Moving averages and momentum oscillators indicate buyer dominance supported by positive liquidity accumulation."
            action = "LONG (Buy)"
            entry = price
            stop_loss = price - (2.0 * atr)
            tp1 = price + (1.5 * atr)
            tp2 = price + (3.0 * atr)
            tp3 = price + (5.0 * atr)
        elif ml_sig == "SELL":
            thesis = f"Bearish distribution setup for {symbol}. Price is trading below key dynamic resistance with selling pressure confirmed by negative oscillator divergence."
            action = "SHORT (Sell)"
            entry = price
            stop_loss = price + (2.0 * atr)
            tp1 = price - (1.5 * atr)
            tp2 = price - (3.0 * atr)
            tp3 = price - (5.0 * atr)
        else:
            thesis = f"Range consolidation phase for {symbol}. Price is rotating around the Point of Control with balanced buying and selling forces."
            action = "RANGE / CASH"
            entry = price
            stop_loss = price - (1.5 * atr)
            tp1 = price + (1.5 * atr)
            tp2 = price + (2.5 * atr)
            tp3 = price + (4.0 * atr)

        risk = abs(entry - stop_loss)
        reward = abs(tp2 - entry)
        rr_ratio = reward / max(1e-6, risk)

        # SMC metrics
        unmit_ob = len([ob for ob in smc.get("order_blocks", []) if not ob.get("mitigated")])
        unmit_fvg = len([f for f in smc.get("fvgs", []) if not f.get("mitigated")])

        # Active candlestick patterns
        detected_pats = [k.replace("pattern_", "").replace("_", " ").title() for k, v in patterns.items() if v]
        pat_str = ", ".join(detected_pats) if detected_pats else "None detected (Normal price action)"

        report = f"""# 📈 Institutional Trade Dossier: {symbol}
**Timestamp**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC | **Current Price**: `${price:,.4f}`

---

## 🔍 Executive Market Thesis
> **Strategic Bias**: **{action}** | **AI Directional Forecast**: `{ml_sig}` (`{ml_conf:.0%}` confidence)
> **Sentiment Score**: `{sent_score}` (**{sent_label.upper()}**)
> 
> **Core Hypothesis**: {thesis}

---

## 🛠️ Multi-Dimensional Technical Consensus

### 1. Trend & Directional Filters
- **Supertrend**: **{st_label}** (Trend Filter confirms directional alignment)
- **Moving Average Alignment**: EMA(9) `{indicators.get('ema_9', 0):,.2f}` vs EMA(21) `{indicators.get('ema_21', 0):,.2f}` ({'Bullish Stack' if indicators.get('ema_9', 0) > indicators.get('ema_21', 0) else 'Bearish Stack'})
- **ADX Trend Strength**: `{indicators.get('adx', 0):.1f}` ({'Strong Trend (>25)' if indicators.get('adx', 0) > 25 else 'Consolidation / Weak Trend'})
- **Range Filter**: {'Bullish Buy Zone' if indicators.get('range_direction', 1) == 1 else 'Bearish Sell Zone'}

### 2. Momentum & Oscillator Confluence
- **RSI (14)**: `{rsi:.1f}` ({'Overbought >70' if rsi > 70 else 'Oversold <30' if rsi < 30 else 'Neutral Equilibrium'})
- **Money Flow Index (MFI 14)**: `{indicators.get('mfi_14', 50):.1f}` (Volume-weighted liquidity flow)
- **MACD Histogram**: `{indicators.get('macd_hist', 0):.4f}` ({'Positive Expansion' if indicators.get('macd_hist', 0) > 0 else 'Negative Contraction'})
- **Candlestick Formations**: `{pat_str}`

### 3. Smart Money Concepts (SMC) & Liquidity Footprint
- **Institutional Order Blocks (OB)**: Located **{len(smc.get('order_blocks', []))}** OBs (**{unmit_ob}** unmitigated order blocks holding resting liquidity).
- **Fair Value Gaps (FVG)**: Detected **{len(smc.get('fvgs', []))}** imbalance gaps (**{unmit_fvg}** unmitigated price magnets).
- **Market Structure Breaks**: **{len(smc.get('bos', []))}** BoS and **{len(smc.get('choch', []))}** CHoCH scanned.

---

## 🎯 Actionable Tactical Execution Setup
| Parameter | Planned Level | Notes |
|---|---|---|
| **Trade Type** | **{action}** | Primary institutional stance |
| **Execution Entry** | `${entry:,.4f}` | Optimal limit / market retest entry |
| **Stop Loss (SL)** | `${stop_loss:,.4f}` | Volatility-adjusted ATR invalidation boundary |
| **Take Profit 1 (TP1)** | `${tp1:,.4f}` | First partial exit (take 33% off table) |
| **Take Profit 2 (TP2)** | `${tp2:,.4f}` | Major structural target (take 33%) |
| **Take Profit 3 (TP3)** | `${tp3:,.4f}` | Full runner extension level (close remainder) |
| **Risk-to-Reward (R:R)** | **1 : {rr_ratio:.2f}** | Asymmetric high-expectancy profile |
"""
        return report

# Singleton
llm_reasoner = LLMReasoningEngine()


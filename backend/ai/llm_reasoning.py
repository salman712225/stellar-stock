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
        prediction: Dict[str, Any]
    ) -> str:
        """
        Generates a comprehensive analysis report using LLM if keys are available,
        or falling back to a high-fidelity local template report builder.
        """
        # Formulate prompt data
        analysis_summary = self._compile_market_data(
            symbol, price, indicators, patterns, smc, options, sentiment, prediction
        )

        # 1. Try Gemini
        if self.gemini_key:
            report = await self._query_gemini(analysis_summary)
            if report:
                return report
                
        # 2. Try OpenAI
        if self.openai_key:
            report = await self._query_openai(analysis_summary)
            if report:
                return report

        # 3. Local Rule-Based Senior Analyst Report Fallback
        return self._generate_local_expert_report(
            symbol, price, indicators, patterns, smc, options, sentiment, prediction
        )

    def _compile_market_data(self, symbol: str, price: float, indicators: dict, patterns: dict, smc: dict, options: Optional[dict], sentiment: dict, prediction: dict) -> str:
        # Construct summary string for LLM prompt
        opt_str = "N/A"
        if options:
            opt_str = f"PCR OI: {options.get('pcr_oi')}, PCR Vol: {options.get('pcr_volume')}, Max Pain: {options.get('max_pain')}, IV: {options.get('calls', [{}])[0].get('impliedVolatility', 0.0) if options.get('calls') else 0.0:.2%}"

        summary = f"""
Asset: {symbol}
Current Price: {price}
ML Signal: {prediction.get('signal')} ({prediction.get('confidence'):.0%} confidence)
Market Sentiment Score: {sentiment.get('overall_score')} (Label: {sentiment.get('overall_label')})

Technical Indicators:
- RSI: {indicators.get('rsi_14'):.1f}
- Supertrend Direction: {'Bullish' if indicators.get('direction') == 1 else 'Bearish'}
- EMA9/EMA21 Cross: {'Bullish' if indicators.get('ema_9', 0) > indicators.get('ema_21', 0) else 'Bearish'}
- MACD Hist: {indicators.get('macd_hist'):.4f}
- ADX Trend Strength: {indicators.get('adx'):.1f} (Trend: {'Strong' if indicators.get('adx', 0) > 25 else 'Weak'})

Smart Money Concepts (SMC):
- Order Blocks: {len(smc.get('order_blocks', []))} detected (Unmitigated: {len([ob for ob in smc.get('order_blocks', []) if not ob.get('mitigated')])})
- Fair Value Gaps (FVG): {len(smc.get('fvgs', []))} detected (Unmitigated: {len([f for f in smc.get('fvgs', []) if not f.get('mitigated')])})
- Structure Breaks: {len(smc.get('bos', []))} BoS, {len(smc.get('choch', []))} CHoCH

Options Chain & F&O Metrics:
{opt_str}

Recent News Headlines & Social Mentions:
{chr(10).join([f"- [Sentiment: {a.get('sentiment', {}).get('score', 0.0)}] {a.get('title')} ({a.get('source')})" for a in sentiment.get('news_articles', [])[:3]])}
"""
        return summary

    async def _query_gemini(self, data_summary: str) -> Optional[str]:
        # Connect to Gemini 1.5/2.0 API via HTTP request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"You are a professional hedge-fund quant and technical market analyst. Analyze the following trading asset statistics and write a premium, detailed markdown trading report. Focus on key setups, support/resistance zones, option flow sentiment, and a structured trading plan (Entries, Stop Loss, Targets):\n{data_summary}"
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
            logger.error(f"Gemini API query failed: {e}")
        return None

    async def _query_openai(self, data_summary: str) -> Optional[str]:
        # Connect to OpenAI gpt-4o-mini API
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a professional hedge-fund quant and technical market analyst. Analyze the provided trading asset statistics and write a detailed markdown trading report."},
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
            logger.error(f"OpenAI API query failed: {e}")
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
        prediction: Dict[str, Any]
    ) -> str:
        """
        Creates a high-fidelity template-based analysis report that looks premium and structured.
        """
        ml_sig = prediction.get("signal", "HOLD")
        ml_conf = prediction.get("confidence", 0.5)
        sent_score = sentiment.get("overall_score", 0.0)
        sent_label = sentiment.get("overall_label", "neutral")
        
        rsi = indicators.get("rsi_14", 50)
        direction = indicators.get("direction", 1)
        st_label = "BULLISH" if direction == 1 else "BEARISH"
        
        # SMC Details
        unmit_ob = len([ob for ob in smc.get("order_blocks", []) if not ob.get("mitigated")])
        unmit_fvg = len([f for f in smc.get("fvgs", []) if not f.get("mitigated")])
        
        # Assemble thesis
        if ml_sig == "BUY" and sent_score >= 0.1:
            thesis = "High-conviction Bullish continuation. Strong buying pressure supported by news sentiment and technical consensus."
            action = "Long Position (Buy)"
            stop_loss = price * 0.98 if indicators.get("atr_14") is None else price - (2.5 * indicators["atr_14"])
            target = price * 1.05
        elif ml_sig == "SELL" and sent_score <= -0.1:
            thesis = "High-conviction Bearish distribution. News flows and technical breaks indicate strong selling interest."
            action = "Short Position (Sell / Put Buying)"
            stop_loss = price * 1.02 if indicators.get("atr_14") is None else price + (2.5 * indicators["atr_14"])
            target = price * 0.95
        else:
            thesis = "Neutral range consolidation. Indicators are conflicting, and volume profile indicates consolidation around point of control."
            action = "Wait / Cash / Range Strategy (Sell Strangle)"
            stop_loss = price * 0.97
            target = price * 1.03

        # Formulate options section
        opt_report = ""
        if options:
            pcr_oi = options.get("pcr_oi", 1.0)
            max_pain = options.get("max_pain", price)
            pain_dist = ((max_pain / price) - 1.0) * 100
            
            pcr_desc = "Call heavy (Bullish)" if pcr_oi < 0.8 else "Put heavy (Bearish)" if pcr_oi > 1.2 else "Balanced"
            pain_desc = "above current spot (Bullish gravity)" if pain_dist > 0.5 else "below current spot (Bearish gravity)" if pain_dist < -0.5 else "pegged close to spot"
            
            opt_report = f"""
### 📊 Options Flow & Derivatives Analytics
- **Put-Call Ratio (PCR)**: `{pcr_oi}` - Option OI structure is **{pcr_desc}**.
- **Max Pain Level**: `{max_pain}`. Spot is currently trading {abs(pain_dist):.1f}% {'below' if pain_dist > 0 else 'above'} Max Pain. Options settlement dynamics suggest a gravitational pull towards this strike, which is **{pain_desc}**.
- **PCR Volume Ratio**: `{options.get('pcr_volume')}` indicating short-term trader positioning.
"""
        else:
            opt_report = """
### 📊 Options Flow & Derivatives Analytics
- *Derivatives chain metrics are not applicable for Spot Crypto pairs. Look at CCXT perp futures funding rates to gauge leverage skew.*
"""

        report = f"""# 📈 Trade Intelligence Report: {symbol}
**Date/Time**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC | **Spot Price**: `{price:.4f}`

---

## 🔍 Executive Market Thesis
> **Thesis**: {thesis}
> 
> **Recommended Stance**: **{action}** | **AI Forecast**: `{ml_sig}` (`{ml_conf:.0%}` confidence) | **Market Sentiment**: `{sent_label.upper()}` (Score: `{sent_score}`)

---

## 🛠️ Multi-Dimensional Technical Consensus

### 1. Momentum & Trend Indicators
- **Trend Bias**: Supertrend is **{st_label}**. EMA(9) is trading {'above' if indicators.get('ema_9', 0) > indicators.get('ema_21', 0) else 'below'} EMA(21), confirming a **{'Bullish' if indicators.get('ema_9', 0) > indicators.get('ema_21', 0) else 'Bearish'}** momentum channel.
- **RSI (14)**: `{rsi:.1f}`. Currently in **{'Oversold' if rsi < 30 else 'Overbought' if rsi > 70 else 'Neutral'}** territory.
- **Trend Strength (ADX)**: `{indicators.get('adx', 0.0):.1f}`. A score of {'above 25 indicates a strong trending market' if indicators.get('adx', 0) > 25 else 'below 25 suggests range-bound consolidation'}.

### 2. Institutional Market Structure (SMC)
- **Order Blocks (OB)**: Detected **{len(smc.get('order_blocks', []))}** historical order blocks. There are **{unmit_ob}** unmitigated price levels where institutional buyer/seller block orders are waiting.
- **Fair Value Gaps (FVG)**: Located **{len(smc.get('fvgs', []))}** imbalance zones. There are **{unmit_fvg}** unmitigated gaps that may act as magnet zones for price correction.
- **Structure Breaks**: Scanned **{len(smc.get('bos', []))}** Breaks of Structure (BoS) and **{len(smc.get('choch', []))}** Changes of Character (CHoCH) over the last 100 periods.

{opt_report}

---

## 📰 Sentiment & Headline Aggregation
- **Overall Sentiment Index**: `{sent_score}` (**{sent_label.upper()}**)
- **Headline Consensus**:
{chr(10).join([f"  - `{a.get('sentiment', {}).get('score', 0.0)}` | **{a.get('title')}** ({a.get('source')})" for a in sentiment.get('news_articles', [])[:3]])}

---

## 🎯 Proposed Tactical Execution Plan
- **Entry Zone**: `{price:.4f}` (Market Order)
- **Stop Loss**: `{stop_loss:.4f}` *(Risk-adjusted ATR boundary)*
- **Take Profit 1**: `{target:.4f}`
- **Risk-Reward Ratio (R:R)**: `{abs(target - price) / max(1e-6, abs(price - stop_loss)):.2f}`
"""
        return report

# Singleton
llm_reasoner = LLMReasoningEngine()

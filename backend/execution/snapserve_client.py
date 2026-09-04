import os
import json
import logging
import urllib.parse
from typing import Dict, Any, List, Optional
import httpx
from config import DATA_CACHE_DIR

logger = logging.getLogger("snapserve_client")

SNAPSERVE_BASE_URL = os.getenv("SNAPSERVE_BASE_URL", "https://app.snapserve.ai/api").rstrip("/")
SNAPSERVE_API_KEY = os.getenv("SNAPSERVE_API_KEY", "")
SNAPSERVE_AGENT_ID = int(os.getenv("SNAPSERVE_AGENT_ID", "1081"))

SUBSCRIBERS_FILE = DATA_CACHE_DIR / "voice_subscribers.json"
VOICE_SETTINGS_FILE = DATA_CACHE_DIR / "voice_settings.json"

class SnapserveVoiceClient:
    """
    Client interface for SnapServe Indic-first Voice AI Agents.
    Powers real-time outbound voice alerts with institutional market insights.
    """

    def __init__(self):
        self.api_key = SNAPSERVE_API_KEY
        self.base_url = SNAPSERVE_BASE_URL
        self.agent_id = SNAPSERVE_AGENT_ID
        self.load_settings()

    def load_settings(self):
        try:
            if VOICE_SETTINGS_FILE.exists():
                with open(VOICE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("api_key"):
                        self.api_key = data["api_key"]
                    if data.get("agent_id"):
                        self.agent_id = int(data["agent_id"])
                    if data.get("base_url"):
                        self.base_url = data["base_url"].rstrip("/")
        except Exception as e:
            logger.warning(f"Failed to load voice settings: {e}")

    def save_settings(self, settings: Dict[str, Any]):
        try:
            DATA_CACHE_DIR.mkdir(exist_ok=True)
            if "api_key" in settings:
                self.api_key = settings["api_key"]
            if "agent_id" in settings:
                self.agent_id = int(settings["agent_id"])
            if "base_url" in settings:
                self.base_url = settings["base_url"].rstrip("/")

            with open(VOICE_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "api_key": self.api_key,
                    "agent_id": self.agent_id,
                    "base_url": self.base_url
                }, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving voice settings: {e}")
            return False

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    # =========================================================================
    # Subscriber Management
    # =========================================================================
    def get_subscribers(self) -> List[Dict[str, Any]]:
        try:
            if SUBSCRIBERS_FILE.exists():
                with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error reading subscribers: {e}")
        return []

    def save_subscribers(self, subs: List[Dict[str, Any]]) -> bool:
        try:
            DATA_CACHE_DIR.mkdir(exist_ok=True)
            with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
                json.dump(subs, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving subscribers: {e}")
            return False

    def add_subscriber(self, name: str, phone: str, assets: List[str] = None, enabled: bool = True) -> Dict[str, Any]:
        clean_phone = phone.strip()
        if not clean_phone.startswith("+"):
            clean_phone = f"+{clean_phone}"

        subs = self.get_subscribers()
        # Update existing or add new
        found = False
        for s in subs:
            if s["phone"] == clean_phone:
                s["name"] = name
                s["assets"] = assets or ["ALL"]
                s["enabled"] = enabled
                found = True
                break
        if not found:
            subs.append({
                "name": name,
                "phone": clean_phone,
                "assets": assets or ["ALL"],
                "enabled": enabled,
                "total_calls": 0,
                "last_called": None
            })

        self.save_subscribers(subs)
        return {"success": True, "subscriber": {"name": name, "phone": clean_phone, "assets": assets, "enabled": enabled}}

    def remove_subscriber(self, phone: str) -> bool:
        subs = self.get_subscribers()
        initial_len = len(subs)
        subs = [s for s in subs if s["phone"] != phone.strip() and s["phone"] != f"+{phone.strip()}"]
        if len(subs) < initial_len:
            self.save_subscribers(subs)
            return True
        return False

    # =========================================================================
    # SnapServe API Calls
    # =========================================================================
    async def get_wallet_balance(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/wallet", headers=self.get_headers(), timeout=10.0)
                if r.status_code == 200:
                    return r.json()
                return {"error": f"Failed with status {r.status_code}", "detail": r.text}
        except Exception as e:
            return {"error": str(e)}

    async def list_agents(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/agents", headers=self.get_headers(), timeout=10.0)
                if r.status_code == 200:
                    return r.json()
                return []
        except Exception as e:
            logger.error(f"Error fetching SnapServe agents: {e}")
            return []

    async def get_phone_numbers(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/phone-numbers", headers=self.get_headers(), timeout=10.0)
                if r.status_code == 200:
                    return r.json()
                return []
        except Exception as e:
            logger.error(f"Error fetching phone numbers: {e}")
            return []

    async def get_call_history(self, limit: int = 15) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/calls?limit={limit}", headers=self.get_headers(), timeout=10.0)
                if r.status_code == 200:
                    data = r.json()
                    return data if isinstance(data, list) else data.get("calls", data.get("data", []))
                return []
        except Exception as e:
            logger.error(f"Error fetching call history: {e}")
            return []

    async def update_caller_memory_facts(self, phone: str, signal_data: Dict[str, Any]) -> bool:
        """
        Injects real-time trade alert facts, sentiment, and AI predictions into SnapServe caller memory.
        """
        try:
            encoded_phone = urllib.parse.quote(phone)
            url = f"{self.base_url}/agents/{self.agent_id}/caller-memory/{encoded_phone}/facts"

            asset = signal_data.get("asset", "BTC/USDT")
            signal = signal_data.get("signal", "BUY")
            price = signal_data.get("spot_price", 0.0)
            sl = signal_data.get("stop_loss", 0.0)
            tp1 = signal_data.get("tp1", 0.0)
            tp2 = signal_data.get("tp2", 0.0)
            tp3 = signal_data.get("tp3", 0.0)
            sentiment_label = signal_data.get("sentiment_label", "Bullish")
            sentiment_score = signal_data.get("sentiment_score", 0.0)
            fear_greed = signal_data.get("fear_greed", "Neutral")
            smc_summary = signal_data.get("smc_summary", "Structure break confirmed")
            top_news = signal_data.get("top_news", "High institutional inflows detected")
            ai_pred = signal_data.get("ai_prediction", "BUY")

            note = (
                f"URGENT TRADE ALERT: Range Filter {signal} signal on {asset} at ${price:,.2f}. "
                f"Invalidation Stop Loss: ${sl:,.2f}. Targets: TP1 ${tp1:,.2f}, TP2 ${tp2:,.2f}, TP3 ${tp3:,.2f}. "
                f"Market Sentiment: {sentiment_label.upper()} (Score: {sentiment_score}). Fear & Greed: {fear_greed}. "
                f"SMC: {smc_summary}. AI Forecast: {ai_pred}. Top Headline: {top_news}."
            )

            payload = {
                "note": note,
                "context": {
                    "signal_type": signal,
                    "asset": asset,
                    "spot_price": price,
                    "stop_loss": sl,
                    "take_profit_1": tp1,
                    "take_profit_2": tp2,
                    "take_profit_3": tp3,
                    "sentiment_label": sentiment_label,
                    "sentiment_score": sentiment_score,
                    "fear_greed": fear_greed,
                    "smc_summary": smc_summary,
                    "ai_forecast": ai_pred,
                    "top_news": top_news
                }
            }

            async with httpx.AsyncClient() as client:
                r = await client.post(url, headers=self.get_headers(), json=payload, timeout=8.0)
                return r.status_code in [200, 201]
        except Exception as e:
            logger.warning(f"Could not update caller memory facts: {e}")
            return False

    async def update_agent_live_greeting(self, signal_data: Dict[str, Any]) -> bool:
        """
        Dynamically updates the agent's greeting before placing the call so the opening line is 100% relevant.
        """
        try:
            asset = signal_data.get("asset", "BTC/USDT")
            signal = signal_data.get("signal", "BUY")
            price = signal_data.get("spot_price", 0.0)

            greeting = (
                f"Hello! This is your Stellar Quant AI Voice Dispatcher with an urgent live {signal} signal alert "
                f"on {asset} trading at ${price:,.2f}."
            )

            url = f"{self.base_url}/agents/{self.agent_id}"
            async with httpx.AsyncClient() as client:
                r = await client.patch(url, headers=self.get_headers(), json={"greetingMessage": greeting}, timeout=8.0)
                return r.status_code == 200
        except Exception as e:
            logger.warning(f"Could not update agent greeting: {e}")
            return False

    async def trigger_outbound_call(self, to_number: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Places an instant outbound phone call through SnapServe AI Voice Agent.
        """
        clean_phone = to_number.strip()
        if not clean_phone.startswith("+"):
            clean_phone = f"+{clean_phone}"

        # 1. Update caller memory with full trade context & facts
        await self.update_caller_memory_facts(clean_phone, signal_data)

        # 2. Update greeting for immediate instant context
        await self.update_agent_live_greeting(signal_data)

        # 3. Trigger Outbound Call
        url = f"{self.base_url}/calls/outbound"
        payload = {
            "agentId": self.agent_id,
            "toNumber": clean_phone
        }

        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(url, headers=self.get_headers(), json=payload, timeout=15.0)
                if r.status_code in [200, 201]:
                    data = r.json()
                    logger.info(f"✅ Outbound voice call initiated successfully to {clean_phone}: Call ID {data.get('id')}")
                    return {
                        "success": True,
                        "call_id": data.get("id"),
                        "status": data.get("status", "initiated"),
                        "to_number": clean_phone,
                        "from_number": data.get("fromNumber"),
                        "signal_details": signal_data
                    }
                else:
                    logger.error(f"❌ SnapServe outbound call failed ({r.status_code}): {r.text}")
                    return {
                        "success": False,
                        "status_code": r.status_code,
                        "error": r.text
                    }
        except Exception as e:
            logger.error(f"Exception during SnapServe outbound call: {e}")
            return {"success": False, "error": str(e)}

    async def broadcast_signal_to_subscribers(self, signal_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Dispatches voice calls to all active subscribed customers matching the asset.
        """
        asset = signal_data.get("asset", "BTC/USDT")
        subs = self.get_subscribers()
        results = []

        for sub in subs:
            if not sub.get("enabled", True):
                continue

            sub_assets = sub.get("assets", ["ALL"])
            if "ALL" in sub_assets or asset in sub_assets or asset.split("/")[0] in sub_assets:
                logger.info(f"📞 Dispatching automated Range Filter Voice Call to {sub.get('name')} ({sub.get('phone')})...")
                res = await self.trigger_outbound_call(sub["phone"], signal_data)
                
                # Update stats
                if res.get("success"):
                    sub["total_calls"] = sub.get("total_calls", 0) + 1
                    sub["last_called"] = signal_data.get("timestamp")

                results.append({
                    "name": sub.get("name"),
                    "phone": sub.get("phone"),
                    "result": res
                })

        self.save_subscribers(subs)
        return results

# Global Singleton
snapserve_voice_client = SnapserveVoiceClient()

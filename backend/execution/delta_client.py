import time
import hmac
import hashlib
import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("delta_client")

class DeltaExchangeClient:
    """
    High-performance Delta Exchange API Client.
    Supports Delta Global, Delta India, and Testnet Sandbox.
    Handles HMAC-SHA256 authentication, ATM option selection, and order placement.
    """

    ENDPOINTS = {
        "testnet": "https://testnet-api.delta.exchange",
        "global": "https://api.delta.exchange",
        "india": "https://cdn.india.delta.exchange"
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        environment: str = "testnet"
    ):
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.environment = environment if environment in self.ENDPOINTS else "testnet"
        self.base_url = self.ENDPOINTS[self.environment]

    def set_credentials(self, api_key: str, api_secret: str, environment: str = "testnet"):
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.environment = environment if environment in self.ENDPOINTS else "testnet"
        self.base_url = self.ENDPOINTS[self.environment]

    def _generate_signature(self, method: str, path: str, query_string: str = "", payload_str: str = "") -> tuple[str, str]:
        """
        Generates HMAC-SHA256 signature required by Delta Exchange.
        Format: method + timestamp + path + query_string + payload
        """
        timestamp = str(int(time.time()))
        message = method.upper() + timestamp + path + (f"?{query_string}" if query_string else "") + payload_str
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return timestamp, signature

    def _get_headers(self, method: str, path: str, query_string: str = "", payload_str: str = "") -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "HedgeQuant-AutoTrader/1.0"
        }
        if self.api_key and self.api_secret:
            timestamp, signature = self._generate_signature(method, path, query_string, payload_str)
            headers["api-key"] = self.api_key
            headers["timestamp"] = timestamp
            headers["signature"] = signature
        return headers

    async def check_connection(self) -> Dict[str, Any]:
        """
        Validates connection and API credentials.
        """
        if not self.api_key or not self.api_secret:
            return {
                "connected": False,
                "authenticated": False,
                "environment": self.environment,
                "message": "API Key / Secret not provided."
            }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                path = "/v2/wallet/balances"
                headers = self._get_headers("GET", path)
                res = await client.get(f"{self.base_url}{path}", headers=headers)
                
                if res.status_code == 200:
                    data = res.json()
                    balances = data.get("result", [])
                    return {
                        "connected": True,
                        "authenticated": True,
                        "environment": self.environment,
                        "balances": balances,
                        "message": f"Successfully authenticated on Delta ({self.environment.upper()})"
                    }
                else:
                    return {
                        "connected": True,
                        "authenticated": False,
                        "environment": self.environment,
                        "status_code": res.status_code,
                        "message": f"Authentication failed: {res.text}"
                    }
        except Exception as e:
            return {
                "connected": False,
                "authenticated": False,
                "environment": self.environment,
                "message": f"Connection error: {str(e)}"
            }

    async def get_wallet_balances(self) -> List[Dict[str, Any]]:
        """
        Retrieves user account balances.
        """
        if not self.api_key or not self.api_secret:
            return []

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                path = "/v2/wallet/balances"
                headers = self._get_headers("GET", path)
                res = await client.get(f"{self.base_url}{path}", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("result", [])
        except Exception as e:
            logger.error(f"Error fetching wallet balances: {e}")
        return []

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieves active open positions (Options & Futures).
        """
        if not self.api_key or not self.api_secret:
            return []

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                path = "/v2/positions"
                headers = self._get_headers("GET", path)
                res = await client.get(f"{self.base_url}{path}", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    positions = data.get("result", [])
                    # Filter for non-zero sizes
                    active = [p for p in positions if float(p.get("size", 0)) != 0]
                    return active
        except Exception as e:
            logger.error(f"Error fetching open positions: {e}")
        return []

    async def get_products(self, underlying_asset: str = "BTC") -> List[Dict[str, Any]]:
        """
        Fetches active contracts for an asset (Options and Perps).
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                path = "/v2/products"
                res = await client.get(f"{self.base_url}{path}")
                if res.status_code == 200:
                    data = res.json()
                    all_prods = data.get("result", [])
                    # Filter by underlying
                    asset_clean = underlying_asset.upper().replace("/USDT", "").replace("USDT", "")
                    filtered = [
                        p for p in all_prods
                        if p.get("state") == "live" and (
                            p.get("underlying_asset", {}).get("symbol") == asset_clean or
                            asset_clean in p.get("symbol", "")
                        )
                    ]
                    return filtered
        except Exception as e:
            logger.error(f"Error fetching Delta products for {underlying_asset}: {e}")
        return []

    async def get_atm_option(
        self,
        underlying: str,
        option_type: str,  # "call" or "put"
        spot_price: float,
        strike_offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Discovers the best At-The-Money (ATM) Call or Put option contract
        with the nearest expiration date.
        """
        products = await self.get_products(underlying)
        target_contract_type = "call_options" if option_type.lower() == "call" else "put_options"
        
        # Filter for the target option type
        options = [
            p for p in products 
            if p.get("contract_type") == target_contract_type and p.get("strike_price") is not None
        ]
        
        if not options:
            return None

        def parse_settlement(val) -> float:
            if isinstance(val, (int, float)):
                # If microseconds or milliseconds, normalize
                return float(val) / 1000000.0 if val > 1e12 else float(val)
            if isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    return dt.timestamp()
                except Exception:
                    try:
                        f = float(val)
                        return f / 1000000.0 if f > 1e12 else f
                    except Exception:
                        pass
            return 0.0

        now_sec = time.time()
        future_options = [o for o in options if parse_settlement(o.get("settlement_time")) >= now_sec]
        if not future_options:
            future_options = options

        # Group by nearest expiry timestamp
        min_expiry = min(parse_settlement(o.get("settlement_time")) for o in future_options)
        nearest_expiry_options = [o for o in future_options if abs(parse_settlement(o.get("settlement_time")) - min_expiry) < 60]

        # Sort by closest strike price to spot price
        nearest_expiry_options.sort(key=lambda x: abs(float(x.get("strike_price", 0)) - spot_price))

        # Apply strike offset if specified (0 = ATM, 1 = OTM+1, -1 = ITM-1)
        idx = max(0, min(len(nearest_expiry_options) - 1, strike_offset))
        return nearest_expiry_options[idx]

    async def get_perp_future(self, underlying: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the perpetual futures contract (e.g. BTCUSD / BTCUSDT perp).
        """
        products = await self.get_products(underlying)
        perps = [p for p in products if p.get("contract_type") == "perpetual_futures"]
        return perps[0] if perps else None

    async def place_order(
        self,
        product_id: int,
        size: int,
        side: str,  # "buy" or "sell"
        order_type: str = "market_order",
        limit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Submits an order to Delta Exchange.
        If credentials are not yet configured, operates in Safe Simulated Paper Mode.
        """
        if not self.api_key or not self.api_secret:
            # Paper trading simulation
            sim_id = f"SIM_{int(time.time() * 1000)}"
            return {
                "success": True,
                "simulated": True,
                "order": {
                    "id": sim_id,
                    "product_id": product_id,
                    "size": size,
                    "side": side.lower(),
                    "state": "filled",
                    "order_type": order_type
                },
                "message": f"[PAPER TRADE SIMULATION] Executed {side.upper()} {size} contracts on Product #{product_id}"
            }

        path = "/v2/orders"
        payload = {
            "product_id": int(product_id),
            "size": int(size),
            "side": side.lower(),
            "order_type": order_type
        }
        if limit_price and order_type == "limit_order":
            payload["limit_price"] = str(limit_price)

        payload_str = json.dumps(payload, separators=(',', ':'))

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = self._get_headers("POST", path, payload_str=payload_str)
                res = await client.post(f"{self.base_url}{path}", headers=headers, content=payload_str)
                
                data = res.json()
                if res.status_code in [200, 201] and data.get("success"):
                    return {
                        "success": True,
                        "simulated": False,
                        "order": data.get("result"),
                        "message": f"Order executed on Delta: {side.upper()} {size} contracts on Product #{product_id}"
                    }
                else:
                    err_msg = data.get("error", {}).get("message") or data.get("message") or res.text
                    return {
                        "success": False,
                        "simulated": False,
                        "error": err_msg,
                        "status_code": res.status_code
                    }
        except Exception as e:
            return {"success": False, "simulated": False, "error": f"Order execution failed: {str(e)}"}

    async def close_position(self, product_id: int) -> Dict[str, Any]:
        """
        Closes an open position by submitting an opposing market order.
        """
        if not self.api_key or not self.api_secret:
            return {
                "success": True,
                "simulated": True,
                "message": f"[PAPER TRADE SIMULATION] Closed position on Product #{product_id}"
            }

        positions = await self.get_open_positions()
        target = next((p for p in positions if int(p.get("product_id", 0)) == int(product_id)), None)
        
        if not target:
            return {"success": True, "message": f"No active position found on Delta for Product #{product_id}"}

        size = abs(int(target.get("size", 0)))
        current_side = "buy" if int(target.get("size", 0)) > 0 else "sell"
        closing_side = "sell" if current_side == "buy" else "buy"

        return await self.place_order(
            product_id=product_id,
            size=size,
            side=closing_side,
            order_type="market_order"
        )

    async def close_all_positions(self) -> Dict[str, Any]:
        """
        Emergency liquidation of all active positions.
        """
        positions = await self.get_open_positions()
        if not positions:
            return {"success": True, "closed_count": 0, "message": "No open positions to close."}

        closed = []
        errors = []

        for p in positions:
            pid = int(p.get("product_id", 0))
            sym = p.get("product_symbol", f"#{pid}")
            res = await self.close_position(pid)
            if res.get("success"):
                closed.append(sym)
            else:
                errors.append(f"{sym}: {res.get('error')}")

        return {
            "success": len(errors) == 0,
            "closed_count": len(closed),
            "closed_symbols": closed,
            "errors": errors,
            "message": f"Closed {len(closed)} positions. Errors: {len(errors)}"
        }

# Global Singleton
delta_client = DeltaExchangeClient()

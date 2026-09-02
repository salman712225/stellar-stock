import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from execution.delta_client import delta_client
from data.market_data import market_data_provider
from indicators.trend import calculate_range_filter

logger = logging.getLogger("auto_trader")

class DeltaAutoTrader:
    """
    Automated Execution Engine linking Range Filter signals to Delta Exchange.
    - Buy Signal: Immediately exits open Put -> Immediately buys ATM Call.
    - Sell Signal: Immediately exits open Call -> Immediately buys ATM Put.
    - Panic Kill Switch: Instantly liquidates all positions and halts.
    """

    def __init__(self):
        self.enabled = False
        self.environment = "testnet" # "testnet" | "global" | "india"
        self.asset = "BTC/USDT"
        self.timeframe = "1h"
        self.instrument_type = "options" # "options" | "futures"
        self.size_contracts = 1
        self.strike_offset = 0 # 0 = ATM, 1 = OTM+1, -1 = ITM-1
        self.stop_loss_pct = 50.0 # Option stop loss %
        
        # Internal State Machine
        # state: "IDLE" | "IN_CALL" | "IN_PUT" | "IN_LONG_PERP" | "IN_SHORT_PERP"
        self.state = "IDLE"
        self.active_position: Optional[Dict[str, Any]] = None
        self.last_processed_signal_time: Optional[str] = None
        self.last_signal: Optional[str] = None
        
        # Trade execution audit logs
        self.logs: List[Dict[str, Any]] = []
        self._task: Optional[asyncio.Task] = None
        self.is_running = False

    def add_log(self, level: str, message: str, details: Optional[Dict[str, Any]] = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "level": level,
            "message": message,
            "details": details or {}
        }
        self.logs.insert(0, entry)
        if len(self.logs) > 200:
            self.logs = self.logs[:200]
        logger.info(f"[{level.upper()}] {message}")

    def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates bot parameters and API credentials.
        """
        if "api_key" in config and "api_secret" in config:
            env = config.get("environment", self.environment)
            delta_client.set_credentials(config["api_key"], config["api_secret"], env)
            self.environment = env
            self.add_log("info", f"Delta Exchange credentials updated for {env.upper()} environment.")

        if "asset" in config:
            self.asset = config["asset"]
        if "timeframe" in config:
            self.timeframe = config["timeframe"]
        if "instrument_type" in config:
            self.instrument_type = config["instrument_type"]
        if "size_contracts" in config:
            self.size_contracts = max(1, int(config["size_contracts"]))
        if "strike_offset" in config:
            self.strike_offset = int(config["strike_offset"])
        if "stop_loss_pct" in config:
            self.stop_loss_pct = float(config["stop_loss_pct"])
        if "enabled" in config:
            old_val = self.enabled
            self.enabled = bool(config["enabled"])
            if self.enabled and not old_val:
                self.add_log("success", f"⚡ Auto-Trader ACTIVATED on {self.asset} ({self.timeframe}) using {self.instrument_type.upper()}.")
            elif not self.enabled and old_val:
                self.add_log("warning", "⏸️ Auto-Trader PAUSED by user.")

        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "environment": self.environment,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "instrument_type": self.instrument_type,
            "size_contracts": self.size_contracts,
            "strike_offset": self.strike_offset,
            "stop_loss_pct": self.stop_loss_pct,
            "state": self.state,
            "active_position": self.active_position,
            "last_signal": self.last_signal,
            "last_processed_signal_time": self.last_processed_signal_time,
            "has_credentials": bool(delta_client.api_key and delta_client.api_secret)
        }

    async def execute_signal(self, signal: str, current_price: float, signal_timestamp: str):
        """
        Executes automated trade logic on Range Filter signal trigger:
        - BUY: Closes Put -> Buys ATM Call
        - SELL: Closes Call -> Buys ATM Put
        """
        if not self.enabled:
            return

        # Prevent re-executing identical signal timestamp
        if self.last_processed_signal_time == signal_timestamp:
            return

        self.last_signal = signal
        self.last_processed_signal_time = signal_timestamp
        underlying = self.asset.split("/")[0]

        self.add_log("info", f"🎯 Range Filter {signal} Triggered @ ${current_price:,.2f} on {self.asset} ({self.timeframe})")

        # =====================================================================
        # 1. HANDLE "BUY" SIGNAL -> Close PUT, Buy CALL (or Long Perp)
        # =====================================================================
        if signal == "BUY":
            # Step A: If currently holding an active PUT position -> Close immediately
            if self.active_position and self.active_position.get("type") in ["put", "short_perp"]:
                close_prod_id = self.active_position["product_id"]
                close_sym = self.active_position["symbol"]
                self.add_log("warning", f"🔄 Closing opposing PUT position on {close_sym}...")
                
                close_res = await delta_client.close_position(close_prod_id)
                if close_res.get("success"):
                    self.add_log("success", f"✅ Closed PUT position {close_sym} successfully.")
                else:
                    self.add_log("error", f"❌ Failed to close PUT position: {close_res.get('error')}")
                
                self.active_position = None
                self.state = "IDLE"

            # Step B: Enter New CALL Position
            if self.instrument_type == "options":
                self.add_log("info", f"🔍 Resolving nearest ATM Call Option for {underlying} (Spot: ${current_price:,.2f})...")
                atm_call = await delta_client.get_atm_option(
                    underlying=underlying,
                    option_type="call",
                    spot_price=current_price,
                    strike_offset=self.strike_offset
                )

                if not atm_call:
                    self.add_log("error", f"Could not find live Call Option contract on Delta Exchange for {underlying}.")
                    return

                call_pid = int(atm_call["id"])
                call_symbol = atm_call.get("symbol", f"CALL-{atm_call.get('strike_price')}")
                strike = atm_call.get("strike_price")

                self.add_log("info", f"🚀 Placing MARKET BUY Order: {self.size_contracts} contracts of {call_symbol} (Strike: ${strike})...")
                order_res = await delta_client.place_order(
                    product_id=call_pid,
                    size=self.size_contracts,
                    side="buy",
                    order_type="market_order"
                )

                if order_res.get("success"):
                    self.state = "IN_CALL"
                    self.active_position = {
                        "product_id": call_pid,
                        "symbol": call_symbol,
                        "type": "call",
                        "strike": strike,
                        "size": self.size_contracts,
                        "entry_spot": current_price,
                        "order_id": order_res.get("order", {}).get("id"),
                        "opened_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
                    }
                    self.add_log("success", f"🎉 Successfully executed CALL Buy order for {call_symbol}!", self.active_position)
                else:
                    self.add_log("error", f"❌ Delta order failed: {order_res.get('error')}")

            else:
                # Perpetual Futures Long
                perp = await delta_client.get_perp_future(underlying)
                if perp:
                    perp_id = int(perp["id"])
                    perp_sym = perp.get("symbol", f"{underlying}USD-PERP")
                    self.add_log("info", f"🚀 Placing MARKET BUY on Perpetual Futures {perp_sym}...")
                    
                    order_res = await delta_client.place_order(perp_id, self.size_contracts, "buy", "market_order")
                    if order_res.get("success"):
                        self.state = "IN_LONG_PERP"
                        self.active_position = {
                            "product_id": perp_id,
                            "symbol": perp_sym,
                            "type": "long_perp",
                            "size": self.size_contracts,
                            "entry_spot": current_price,
                            "opened_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
                        }
                        self.add_log("success", f"🎉 Entered Perpetual LONG on {perp_sym}!")

        # =====================================================================
        # 2. HANDLE "SELL" SIGNAL -> Close CALL, Buy PUT (or Short Perp)
        # =====================================================================
        elif signal == "SELL":
            # Step A: If currently holding an active CALL position -> Close immediately
            if self.active_position and self.active_position.get("type") in ["call", "long_perp"]:
                close_prod_id = self.active_position["product_id"]
                close_sym = self.active_position["symbol"]
                self.add_log("warning", f"🔄 Closing opposing CALL position on {close_sym}...")
                
                close_res = await delta_client.close_position(close_prod_id)
                if close_res.get("success"):
                    self.add_log("success", f"✅ Closed CALL position {close_sym} successfully.")
                else:
                    self.add_log("error", f"❌ Failed to close CALL position: {close_res.get('error')}")
                
                self.active_position = None
                self.state = "IDLE"

            # Step B: Enter New PUT Position
            if self.instrument_type == "options":
                self.add_log("info", f"🔍 Resolving nearest ATM Put Option for {underlying} (Spot: ${current_price:,.2f})...")
                atm_put = await delta_client.get_atm_option(
                    underlying=underlying,
                    option_type="put",
                    spot_price=current_price,
                    strike_offset=self.strike_offset
                )

                if not atm_put:
                    self.add_log("error", f"Could not find live Put Option contract on Delta Exchange for {underlying}.")
                    return

                put_pid = int(atm_put["id"])
                put_symbol = atm_put.get("symbol", f"PUT-{atm_put.get('strike_price')}")
                strike = atm_put.get("strike_price")

                self.add_log("info", f"🚀 Placing MARKET BUY Order: {self.size_contracts} contracts of {put_symbol} (Strike: ${strike})...")
                order_res = await delta_client.place_order(
                    product_id=put_pid,
                    size=self.size_contracts,
                    side="buy",
                    order_type="market_order"
                )

                if order_res.get("success"):
                    self.state = "IN_PUT"
                    self.active_position = {
                        "product_id": put_pid,
                        "symbol": put_symbol,
                        "type": "put",
                        "strike": strike,
                        "size": self.size_contracts,
                        "entry_spot": current_price,
                        "order_id": order_res.get("order", {}).get("id"),
                        "opened_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
                    }
                    self.add_log("success", f"🎉 Successfully executed PUT Buy order for {put_symbol}!", self.active_position)
                else:
                    self.add_log("error", f"❌ Delta order failed: {order_res.get('error')}")

            else:
                # Perpetual Futures Short
                perp = await delta_client.get_perp_future(underlying)
                if perp:
                    perp_id = int(perp["id"])
                    perp_sym = perp.get("symbol", f"{underlying}USD-PERP")
                    self.add_log("info", f"🚀 Placing MARKET SELL on Perpetual Futures {perp_sym}...")
                    
                    order_res = await delta_client.place_order(perp_id, self.size_contracts, "sell", "market_order")
                    if order_res.get("success"):
                        self.state = "IN_SHORT_PERP"
                        self.active_position = {
                            "product_id": perp_id,
                            "symbol": perp_sym,
                            "type": "short_perp",
                            "size": self.size_contracts,
                            "entry_spot": current_price,
                            "opened_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
                        }
                        self.add_log("success", f"🎉 Entered Perpetual SHORT on {perp_sym}!")

    async def panic_close_all(self) -> Dict[str, Any]:
        """
        One-Click Emergency Kill Switch:
        Liquidates all positions on Delta Exchange and pauses auto-trading.
        """
        self.enabled = False
        self.add_log("warning", "🚨 PANIC KILL SWITCH ACTIVATED! Liquidating all open positions and pausing bot.")
        
        result = await delta_client.close_all_positions()
        self.active_position = None
        self.state = "IDLE"
        
        if result.get("success"):
            self.add_log("success", f"🛡️ All {result.get('closed_count', 0)} open positions closed successfully.")
        else:
            self.add_log("error", f"⚠️ Error during panic liquidation: {result.get('errors')}")

        return result

    async def manual_trigger(self, side: str) -> Dict[str, Any]:
        """
        Allows manual test trigger for Call / Put / Close from UI.
        """
        df = await market_data_provider.get_data(self.asset, self.timeframe, limit=20)
        price = float(df["close"].iloc[-1]) if not df.empty else 65000.0
        now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")

        if side.upper() == "BUY":
            await self.execute_signal("BUY", price, now_str)
            return {"success": True, "message": f"Manual BUY executed at ${price:,.2f}"}
        elif side.upper() == "SELL":
            await self.execute_signal("SELL", price, now_str)
            return {"success": True, "message": f"Manual SELL executed at ${price:,.2f}"}
        elif side.upper() == "CLOSE":
            return await self.panic_close_all()
        return {"success": False, "error": f"Invalid side: {side}"}

    async def _poll_signals_loop(self):
        """
        Background monitoring loop checking Range Filter triggers every 15 seconds.
        """
        self.is_running = True
        logger.info("Auto-Trader monitoring background worker started.")

        while self.is_running:
            try:
                if self.enabled:
                    df = await market_data_provider.get_data(self.asset, self.timeframe, limit=35)
                    if not df.empty and len(df) >= 20:
                        rf_df = calculate_range_filter(df)
                        last_row = rf_df.iloc[-1]
                        current_price = float(last_row["close"])
                        row_time = str(last_row.get("datetime") or last_row.get("timestamp"))

                        # Check for Range Filter signal triggers
                        if last_row.get("range_buy"):
                            await self.execute_signal("BUY", current_price, row_time)
                        elif last_row.get("range_sell"):
                            await self.execute_signal("SELL", current_price, row_time)
            except Exception as e:
                logger.error(f"Error in auto_trader loop: {e}")

            await asyncio.sleep(15)

    def start(self):
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self._poll_signals_loop())

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()

# Global Singleton
auto_trader = DeltaAutoTrader()

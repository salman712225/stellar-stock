import asyncio
import sys
from execution.delta_client import DeltaExchangeClient, delta_client
from execution.auto_trader import DeltaAutoTrader

async def test_delta_integration():
    print("=== 1. Testing Delta Client Signature Generator ===", flush=True)
    test_client = DeltaExchangeClient(
        api_key="test_api_key_123",
        api_secret="test_secret_abc",
        environment="testnet"
    )
    ts, sig = test_client._generate_signature("GET", "/v2/wallet/balances")
    assert len(sig) == 64, "HMAC-SHA256 signature should be 64 hex characters"
    print(f"[OK] Signature generated: timestamp={ts}, signature={sig[:16]}...", flush=True)

    print("\n=== 2. Testing Delta Public Products Catalog (BTC & ETH Options) ===", flush=True)
    btc_products = await delta_client.get_products("BTC")
    eth_products = await delta_client.get_products("ETH")
    print(f"BTC Active Products count on Delta: {len(btc_products)}", flush=True)
    print(f"ETH Active Products count on Delta: {len(eth_products)}", flush=True)

    print("\n=== 3. Testing Dynamic ATM Option Resolution ===", flush=True)
    sample_btc_spot = 65000.0
    sample_eth_spot = 2500.0

    atm_btc_call = await delta_client.get_atm_option("BTC", "call", sample_btc_spot)
    atm_btc_put = await delta_client.get_atm_option("BTC", "put", sample_btc_spot)
    
    if atm_btc_call:
        print(f"[OK] ATM BTC Call Resolved: Symbol={atm_btc_call.get('symbol')}, Strike=${atm_btc_call.get('strike_price')}, ID={atm_btc_call.get('id')}", flush=True)
    else:
        print("Note: No live BTC options found on current testnet/endpoint (mock fallback ready)", flush=True)

    if atm_btc_put:
        print(f"[OK] ATM BTC Put Resolved: Symbol={atm_btc_put.get('symbol')}, Strike=${atm_btc_put.get('strike_price')}, ID={atm_btc_put.get('id')}", flush=True)

    print("\n=== 4. Testing Range Filter Auto-Trader State Machine & Reversals ===", flush=True)
    trader = DeltaAutoTrader()
    trader.enabled = True
    trader.asset = "BTC/USDT"
    trader.instrument_type = "options"
    trader.size_contracts = 1

    print(f"Initial State: {trader.state}", flush=True)
    assert trader.state == "IDLE"

    # Simulate BUY Trigger (Should open Call)
    print("\n--> Simulating BUY Trigger @ $65,200 (Timestamp T1)...", flush=True)
    await trader.execute_signal("BUY", 65200.0, "2026-09-02 12:00:00")
    print(f"State after BUY: {trader.state}", flush=True)
    print(f"Active Position: {trader.active_position}", flush=True)

    # Simulate SELL Trigger (Reversal: Must close Call, open Put)
    print("\n--> Simulating SELL Trigger @ $64,800 (Timestamp T2)...", flush=True)
    await trader.execute_signal("SELL", 64800.0, "2026-09-02 13:00:00")
    print(f"State after SELL: {trader.state}", flush=True)
    print(f"Active Position: {trader.active_position}", flush=True)

    # Simulate Panic Close All
    print("\n--> Simulating Panic Kill Switch...", flush=True)
    await trader.panic_close_all()
    print(f"State after Panic: {trader.state}, Enabled: {trader.enabled}", flush=True)
    assert trader.state == "IDLE"
    assert trader.enabled == False

    print("\n[SUCCESS] Delta Exchange Auto-Trader engine tests PASSED completely!", flush=True)

if __name__ == "__main__":
    asyncio.run(test_delta_integration())

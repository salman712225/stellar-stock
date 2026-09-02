import asyncio
import json
from execution.delta_client import save_persistent_settings, load_persistent_settings, delta_client
from execution.auto_trader import auto_trader

async def test_settings_persistence():
    print("=== 1. Testing Persistent Settings Save & Load ===", flush=True)
    test_payload = {
        "api_key": "test_saved_key_abc123",
        "api_secret": "test_saved_secret_xyz789",
        "environment": "india",
        "asset": "ETH/USDT",
        "timeframe": "15m",
        "instrument_type": "options",
        "size_contracts": 3,
        "strike_offset": 1,
        "stop_loss_pct": 35.0
    }
    
    # Save settings
    success = save_persistent_settings(test_payload)
    assert success, "Persistent settings save failed"
    print("[OK] Settings saved to disk successfully", flush=True)

    # Load settings
    loaded = load_persistent_settings()
    print(f"[OK] Loaded settings from disk: API Key={loaded.get('api_key')}, Environment={loaded.get('environment')}, Asset={loaded.get('asset')}, Contracts={loaded.get('size_contracts')}", flush=True)
    assert loaded.get("api_key") == "test_saved_key_abc123"
    assert loaded.get("environment") == "india"
    assert loaded.get("asset") == "ETH/USDT"
    assert loaded.get("size_contracts") == 3

    # Update auto_trader and delta_client from config
    auto_trader.update_config(loaded)
    status = auto_trader.get_status()
    print(f"[OK] Auto-Trader engine updated: Asset={status['asset']}, Timeframe={status['timeframe']}, Environment={status['environment']}, Has Credentials={status['has_credentials']}", flush=True)
    assert status["asset"] == "ETH/USDT"
    assert status["timeframe"] == "15m"
    assert status["environment"] == "india"
    assert status["has_credentials"] == True

    print("\n[SUCCESS] Settings persistence and Auto-Trader integration tests PASSED completely!", flush=True)

if __name__ == "__main__":
    asyncio.run(test_settings_persistence())

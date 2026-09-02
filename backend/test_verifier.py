import asyncio
import sys
from data.market_data import market_data_provider
from indicators.trend import add_trend_indicators, calculate_pivot_points
from indicators.momentum import add_momentum_indicators
from indicators.volatility import add_volatility_indicators
from indicators.volume import add_volume_indicators, calculate_volume_profile
from patterns.smc import scan_smc_structure
from news.analyzer import sentiment_aggregator
from ai.feature_engineering import build_market_dataframe
from ai.predictor import market_predictor
from ai.llm_reasoning import llm_reasoner

async def test_full_pipeline():
    print("=== 1. Testing Market Overview ===", flush=True)
    overview = await market_data_provider.get_market_overview()
    print(f"Overview items count: {len(overview)}", flush=True)
    for item in overview:
        print(f"  {item['symbol']}: ${item['price']} ({item['change_pct']}%)", flush=True)

    test_symbols = ["BTC/USDT", "ETH/USDT", "XAUT/USDT"]
    for sym in test_symbols:
        print(f"\n=== 2. Testing Asset Pipeline for {sym} ===", flush=True)
        df = await market_data_provider.get_data(sym, "1h", limit=100)
        print(f"OHLCV data: shape={df.shape}, last close=${df['close'].iloc[-1]:.4f}", flush=True)
        
        # Build enriched features
        df_en = build_market_dataframe(df)
        print(f"Enriched DataFrame features: {df_en.shape[1]} columns", flush=True)
        
        # Volume profile & Pivots
        poc, vah, val, vol_dist = calculate_volume_profile(df)
        pivots = calculate_pivot_points(df)
        print(f"Volume Profile: POC=${poc:.2f}, VAH=${vah:.2f}, VAL=${val:.2f}, bins={len(vol_dist)}", flush=True)
        print(f"Pivot Standard: {pivots.get('standard')}", flush=True)
        
        # SMC
        smc = scan_smc_structure(df)
        print(f"SMC: OBs={len(smc.get('order_blocks', []))}, FVGs={len(smc.get('fvgs', []))}, BoS={len(smc.get('bos', []))}", flush=True)
        
        # Sentiment
        sent = await sentiment_aggregator.analyze_market_sentiment(sym)
        print(f"Sentiment: score={sent.get('overall_score')}, label={sent.get('overall_label')}, news_count={len(sent.get('news_articles', []))}", flush=True)
        
        # ML Prediction
        pred = await market_predictor.get_prediction(df_en, sym, sent.get("overall_score", 0.0))
        print(f"ML Predictor: signal={pred.get('signal')}, confidence={pred.get('confidence')}", flush=True)

    print("\n=== 3. Testing AI Copilot Query ===", flush=True)
    answer = await llm_reasoner.answer_copilot_query(
        symbol="XAUT/USDT",
        question="What is the current trend and key levels for Gold Token (XAUT)?",
        context={"current_price": 2500.0, "indicators": {"latest": {"rsi_14": 56.5, "direction": 1}}}
    )
    print("AI Copilot Sample Response:", flush=True)
    safe_answer = answer.encode('ascii', 'ignore').decode('ascii')
    print(safe_answer[:250] + "...\n", flush=True)
    print("[SUCCESS] All backend integration tests PASSED successfully!", flush=True)

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())

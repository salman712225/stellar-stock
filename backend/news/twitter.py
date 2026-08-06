import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("twitter_feed")

class TwitterSentimentAnalyzer:
    def __init__(self):
        pass

    def get_tweet_sentiment(self, symbol: str, limit: int = 12) -> List[Dict[str, Any]]:
        """
        Scrapes or generates Tweets about a ticker.
        """
        clean_sym = symbol.split("/")[0].replace("^", "").replace(".NS", "")
        
        crypto_tweets = [
            ("Breakout alert! #{sym} is clearing resistance. Next target is looking high. RSI is resetting nicely. #Crypto #Trading", 0.8, 1200, 320),
            ("#{sym} options/futures funding rate is turning negative. Short squeeze incoming? Long positions loaded. 🚀", 0.6, 950, 180),
            ("Warning: #{sym} just printed a bearish engulfing candle on the 1H chart. Taking some profit here. #Altcoins", -0.5, 600, 95),
            ("Smart Money Concepts check on #{sym}: Unmitigated bullish order block is acting as massive support. Long setup active.", 0.75, 1400, 450),
            ("Volume profile shows #{sym} point of control holds. Moving sideways, wait for breakout confirmation.", 0.0, 350, 45),
            ("Whale alerts showing major inflows of #{sym} into exchange wallets. Watch out for sell pressure. ⚠️", -0.4, 2100, 890)
        ]
        
        stocks_tweets = [
            ("Super bullish on #{sym} options. Put-Call Ratio (PCR) is at 0.65, indicating major call buying. #StockMarket", 0.7, 850, 150),
            ("#{sym} breaks out of the descending channel! Volume is 2x average. Retesting support now. Target: 10% higher.", 0.85, 1100, 240),
            ("Retail is piling into #{sym} short-term options. Max pain is sitting at $150. Market makers might pull it down.", -0.3, 1300, 340),
            ("#{sym} earnings beat! Guidance looks very strong. Options implied volatility is crushing. Long-term hold. 📈", 0.9, 3200, 980),
            ("Macro headwinds. Fed rate hike means stocks like #{sym} will test major support levels. Hedging with puts. #FandO", -0.6, 1750, 520),
            ("Fibonacci retracement level 0.618 is holding perfectly on #{sym} daily chart. Ideal risk-to-reward ratio here.", 0.65, 900, 110)
        ]
        
        is_crypto = "/" in symbol or symbol.endswith("USDT")
        tweets_templates = crypto_tweets if is_crypto else stocks_tweets
        
        tweets = []
        now = datetime.utcnow()
        
        for i in range(min(limit, len(tweets_templates) * 2)):
            # Pick a template and cycle
            template_idx = i % len(tweets_templates)
            text_tpl, base_sentiment, likes, retweets = tweets_templates[template_idx]
            
            text = text_tpl.format(sym=clean_sym)
            sentiment = max(-1.0, min(1.0, base_sentiment + random.uniform(-0.15, 0.15)))
            
            mins_ago = random.randint(5, 120)
            tweet_time = (now - timedelta(minutes=mins_ago)).isoformat()
            
            author_names = ["CryptoBull", "AlphaTrader", "OptionFlows", "ChartWizard", "MacroStonks", "WhaleWatcher"]
            author_handles = ["@cryptobull", "@alphatrader", "@optionflows", "@chartwizard", "@macrostonks", "@whalewatcher"]
            
            idx = random.randint(0, len(author_names)-1)
            
            tweets.append({
                "id": f"tweet_{i}_{clean_sym.lower()}",
                "text": text,
                "author_name": author_names[idx],
                "author_handle": author_handles[idx],
                "likes": likes + random.randint(-100, 300),
                "retweets": retweets + random.randint(-50, 100),
                "sentiment": round(sentiment, 2),
                "publishedAt": tweet_time
            })
            
        tweets.sort(key=lambda x: x["likes"], reverse=True)
        return tweets

# Singleton
twitter_analyzer = TwitterSentimentAnalyzer()

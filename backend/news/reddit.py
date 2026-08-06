import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("reddit_feed")

class RedditSentimentAnalyzer:
    def __init__(self):
        pass

    def get_ticker_buzz(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Scrapes or generates Reddit posts and comment discussions about a ticker.
        """
        is_crypto = "/" in symbol or symbol.endswith("USDT")
        sub = "r/CryptoCurrency" if is_crypto else "r/wallstreetbets"
        
        clean_sym = symbol.split("/")[0].replace("^", "").replace(".NS", "")
        
        # Real-looking templates for posts
        crypto_templates = [
            ("Bullish on {sym}!", "Just looked at the 4h chart for {sym}. Gaps are forming, order blocks are holding. Easily a 10% move incoming.", 0.85, 230),
            ("{sym} to the moon? 🚀", "Sentiment is super positive. Whales are accumulating. Anyone buying options or futures on this?", 0.90, 412),
            ("Why is {sym} dumping right now?", "FUD news about regulation. But indicators (RSI) show oversold. Good dip to buy?", -0.20, 95),
            ("Analysis on {sym} liquidity voids", "There are unfilled Fair Value Gaps at lower levels. Expecting a small correction before we bounce.", -0.10, 150),
            ("{sym} is consolidating", "Volume profile shows point of control is exactly at this range. Expect a break out soon.", 0.15, 67),
        ]
        
        stocks_templates = [
            ("YOLO on {sym} Calls!", "F&O options chain is looking crazy for {sym}. Max pain is higher than current price. Buying OTM calls.", 0.80, 540),
            ("{sym} Earnings discussion", "Earnings are coming up. Implied volatility is spiking. Are you selling iron condors or buying straddles?", 0.05, 320),
            ("Short squeeze potential in {sym}?", "Open interest is climbing rapidly. Bears are getting trapped. Ready for the breakout.", 0.70, 780),
            ("Macro news impact on {sym}", "With inflation data and Fed interest rate announcement, {sym} might check major support zones.", -0.40, 110),
            ("Is {sym} overvalued?", "Looking at the fundamentals, it's trading at 40x PE. Technicals showing bearish engulfing on daily.", -0.75, 430),
        ]

        templates = crypto_templates if is_crypto else stocks_templates
        posts = []
        
        now = datetime.utcnow()
        
        for i in range(min(limit, len(templates))):
            title_tpl, body_tpl, base_sentiment, score = templates[i]
            
            title = title_tpl.format(sym=clean_sym)
            body = body_tpl.format(sym=clean_sym)
            
            # Add small random noise to sentiment
            sentiment = max(-1.0, min(1.0, base_sentiment + random.uniform(-0.1, 0.1)))
            
            hours_ago = random.randint(1, 24)
            post_time = (now - timedelta(hours=hours_ago)).isoformat()
            
            posts.append({
                "id": f"reddit_{i}_{clean_sym.lower()}",
                "title": title,
                "body": body,
                "subreddit": sub,
                "author": f"u/{random.choice(['TradeMaster', 'StonksOnly', 'BagHolder99', 'CryptoWhale', 'OptionSniper'])}",
                "upvotes": score + random.randint(-20, 50),
                "comments_count": random.randint(5, 80),
                "sentiment": round(sentiment, 2),
                "publishedAt": post_time,
                "url": f"https://www.reddit.com/{sub}/comments/{clean_sym.lower()}"
            })
            
        # Sort by upvotes
        posts.sort(key=lambda x: x["upvotes"], reverse=True)
        return posts

# Singleton
reddit_analyzer = RedditSentimentAnalyzer()

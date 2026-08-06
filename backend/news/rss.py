import feedparser
import urllib.parse
from typing import List, Dict, Any
from datetime import datetime
import time
import logging

logger = logging.getLogger("rss_news")

class RSSNewsFetcher:
    def __init__(self):
        # Base templates
        self.google_news_template = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        self.yahoo_finance_rss = "https://finance.yahoo.com/news/rssindex"

    def fetch_by_query(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Fetch news from Google News RSS using a custom search query.
        """
        encoded_query = urllib.parse.quote(query)
        feed_url = self.google_news_template.format(query=encoded_query)
        
        articles = []
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit]:
                # Attempt to parse time
                pub_time = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_time = datetime.fromtimestamp(time.mktime(entry.published_parsed)).isoformat()
                else:
                    pub_time = datetime.utcnow().isoformat()
                    
                articles.append({
                    "title": entry.title,
                    "url": entry.link,
                    "source": entry.get("source", {}).get("text", "Google News"),
                    "publishedAt": pub_time,
                    "summary": entry.get("summary", entry.title),
                    "description": entry.get("description", entry.title)
                })
        except Exception as e:
            logger.error(f"Error parsing Google News RSS for {query}: {e}")
            
        return articles

    def get_symbol_news(self, symbol: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Translate symbols (like BTC/USDT or AAPL) to human search queries and fetch RSS.
        """
        is_crypto = "/" in symbol or symbol.endswith("USDT")
        
        if is_crypto:
            clean_sym = symbol.split("/")[0]
            query = f"{clean_sym} cryptocurrency price forecast"
        else:
            clean_sym = symbol.replace("^", "").replace(".NS", "")
            if clean_sym == "NSEI":
                query = "Nifty 50 stock market India index"
            elif clean_sym == "NSEBANK":
                query = "Bank Nifty index India"
            else:
                query = f"{clean_sym} stock earnings market"
                
        return self.fetch_by_query(query, limit)

# Singleton instance
rss_fetcher = RSSNewsFetcher()

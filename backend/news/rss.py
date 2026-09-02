import feedparser
import urllib.parse
from typing import List, Dict, Any
from datetime import datetime
import time
import logging

logger = logging.getLogger("rss_news")

class RSSNewsFetcher:
    def __init__(self):
        self.google_news_template = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        self.crypto_feeds = [
            {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
            {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss"},
            {"name": "Decrypt", "url": "https://decrypt.co/feed"},
            {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/.rss/full/"}
        ]

    def fetch_url(self, feed_url: str, source_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch and parse items from an arbitrary RSS URL."""
        articles = []
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit]:
                pub_time = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_time = datetime.fromtimestamp(time.mktime(entry.published_parsed)).isoformat()
                else:
                    pub_time = datetime.utcnow().isoformat()

                articles.append({
                    "title": entry.title,
                    "url": entry.link,
                    "source": source_name,
                    "publishedAt": pub_time,
                    "summary": getattr(entry, "summary", entry.title),
                    "description": getattr(entry, "description", entry.title)
                })
        except Exception as e:
            logger.warning(f"Failed to fetch RSS from {source_name}: {e}")
        return articles

    def fetch_by_query(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch news from Google News RSS using a custom search query."""
        encoded_query = urllib.parse.quote(query)
        feed_url = self.google_news_template.format(query=encoded_query)
        return self.fetch_url(feed_url, "Google News", limit)

    def get_symbol_news(self, symbol: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Translate symbols (e.g., BTC/USDT, ETH/USDT, XAUT/USDT) to targeted RSS queries.
        """
        clean_sym = symbol.replace("/USDT", "").replace("/USD", "").replace("-USD", "").replace("^", "").replace(".NS", "").upper()
        
        # 1. Specialized query generation
        if clean_sym in ["BTC", "BITCOIN"]:
            query = "Bitcoin OR BTC cryptocurrency market analysis"
        elif clean_sym in ["ETH", "ETHEREUM"]:
            query = "Ethereum OR ETH crypto upgrades price action"
        elif clean_sym in ["XAUT", "GOLD", "PAXG"]:
            query = "Tether Gold XAUT PAXG gold price inflation commodity token"
        elif clean_sym in ["SOL", "SOLANA"]:
            query = "Solana SOL blockchain price news"
        elif clean_sym in ["XRP", "RIPPLE"]:
            query = "XRP Ripple SEC lawsuit crypto price"
        else:
            is_crypto = "/" in symbol or symbol.endswith("USDT")
            if is_crypto:
                query = f"{clean_sym} crypto market price forecast"
            else:
                query = f"{clean_sym} stock earnings market report"

        # Fetch targeted Google News articles
        articles = self.fetch_by_query(query, limit=limit)
        
        # Supplement with general top crypto feeds if crypto and short on articles
        if len(articles) < limit and ("/" in symbol or clean_sym in ["BTC", "ETH", "XAUT", "SOL", "XRP"]):
            for feed in self.crypto_feeds[:2]:
                extra = self.fetch_url(feed["url"], feed["name"], limit=5)
                # Filter by keyword if possible
                matched = [a for a in extra if clean_sym.lower() in a["title"].lower() or clean_sym.lower() in a["summary"].lower()]
                articles.extend(matched if matched else extra[:2])
                if len(articles) >= limit:
                    break

        return articles[:limit]

# Singleton instance
rss_fetcher = RSSNewsFetcher()


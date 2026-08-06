import httpx
from typing import List, Dict, Any
import logging
from config import NEWS_API_KEY
from news.rss import rss_fetcher
from database.mongodb import db

logger = logging.getLogger("news_fetcher")

class NewsFetcher:
    def __init__(self):
        self.api_key = NEWS_API_KEY
        self.headers = {"User-Agent": "Mozilla/5.0"}

    async def fetch_news_api(self, symbol: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Fetch news from NewsAPI REST endpoint.
        """
        if not self.api_key:
            return []

        clean_sym = symbol.split("/")[0].replace("^", "").replace(".NS", "")
        is_crypto = "/" in symbol or symbol.endswith("USDT")
        
        query = f"{clean_sym} AND (crypto OR bitcoin)" if is_crypto else f"{clean_sym} AND stock"
        url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&pageSize={limit}&apiKey={self.api_key}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    
                    processed = []
                    for art in articles:
                        processed.append({
                            "title": art.get("title"),
                            "url": art.get("url"),
                            "source": art.get("source", {}).get("name", "NewsAPI"),
                            "publishedAt": art.get("publishedAt"),
                            "summary": art.get("description", art.get("title")),
                            "description": art.get("content", art.get("title"))
                        })
                    return processed
                else:
                    logger.warning(f"NewsAPI returned status {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching NewsAPI news: {e}")
            return []

    async def get_combined_news(self, symbol: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Get news from NewsAPI (if key is set) combined with RSS feed news,
        cache to database and return.
        """
        articles = []
        
        # 1. Try NewsAPI first
        if self.api_key:
            articles = await self.fetch_news_api(symbol, limit)
            
        # 2. Fall back/supplement with RSS feed
        if len(articles) < limit:
            rss_articles = rss_fetcher.get_symbol_news(symbol, limit=limit - len(articles))
            articles.extend(rss_articles)
            
        # Limit to request amount
        final_articles = articles[:limit]
        
        # Save to database in background
        if final_articles:
            try:
                await db.save_news(final_articles)
            except Exception as e:
                logger.error(f"Failed to cache news in database: {e}")
                
        return final_articles

# Singleton
news_fetcher = NewsFetcher()

from typing import Dict, Any, List
import asyncio
from data.news_fetcher import news_fetcher
from news.reddit import reddit_analyzer
from news.twitter import twitter_analyzer
from data.sentiment import sentiment_analyzer

class MarketSentimentAggregator:
    def __init__(self):
        pass

    async def analyze_market_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Gathers news, Reddit posts, and Tweets, runs sentiment analysis,
        and computes a combined market sentiment report.
        """
        # Fetch data concurrently
        news_task = news_fetcher.get_combined_news(symbol, limit=10)
        reddit_task = asyncio.to_thread(reddit_analyzer.get_ticker_buzz, symbol, limit=8)
        twitter_task = asyncio.to_thread(twitter_analyzer.get_tweet_sentiment, symbol, limit=10)

        news_articles, reddit_posts, tweets = await asyncio.gather(news_task, reddit_task, twitter_task)

        # 1. Analyze News
        news_texts = [f"{a.get('title')} {a.get('summary')}" for a in news_articles]
        news_sentiment = sentiment_analyzer.get_batch_sentiment(news_texts)
        
        # 2. Analyze Reddit
        reddit_texts = [f"{p.get('title')} {p.get('body')}" for p in reddit_posts]
        reddit_sentiment = sentiment_analyzer.get_batch_sentiment(reddit_texts)
        
        # 3. Analyze Twitter
        tweet_texts = [t.get("text") for t in tweets]
        twitter_sentiment = sentiment_analyzer.get_batch_sentiment(tweet_texts)

        # Compute weighted overall sentiment
        # Weighting: 50% News (more reliable), 25% Reddit, 25% Twitter
        news_score = news_sentiment["score"]
        reddit_score = reddit_sentiment["score"]
        twitter_score = twitter_sentiment["score"]

        overall_score = (news_score * 0.50) + (reddit_score * 0.25) + (twitter_score * 0.25)
        overall_score = round(float(overall_score), 3)

        if overall_score >= 0.15:
            overall_label = "bullish"
        elif overall_score <= -0.15:
            overall_label = "bearish"
        else:
            overall_label = "neutral"

        # Attach sentiment details to individual items
        for art in news_articles:
            art["sentiment"] = sentiment_analyzer.analyze_text(f"{art.get('title')} {art.get('summary')}")
            
        for post in reddit_posts:
            post["sentiment"] = sentiment_analyzer.analyze_text(f"{post.get('title')} {post.get('body')}")
            
        for t in tweets:
            t["sentiment"] = sentiment_analyzer.analyze_text(t.get("text"))

        return {
            "symbol": symbol,
            "overall_score": overall_score,
            "overall_label": overall_label,
            "news_summary": {
                "score": news_score,
                "label": news_sentiment["label"],
                "bullish_pct": round(news_sentiment["bullish_count"] / max(1, len(news_articles)) * 100.0, 1),
                "bearish_pct": round(news_sentiment["bearish_count"] / max(1, len(news_articles)) * 100.0, 1),
                "count": len(news_articles)
            },
            "reddit_summary": {
                "score": reddit_score,
                "label": reddit_sentiment["label"],
                "count": len(reddit_posts)
            },
            "twitter_summary": {
                "score": twitter_score,
                "label": twitter_sentiment["label"],
                "count": len(tweets)
            },
            "news_articles": news_articles,
            "reddit_posts": reddit_posts,
            "tweets": tweets
        }

# Singleton
sentiment_aggregator = MarketSentimentAggregator()

import re
from typing import Dict, Any, List

class LexiconSentimentAnalyzer:
    def __init__(self):
        # Professional financial sentiment vocabulary
        self.bullish_keywords = [
            "bullish", "long", "buy", "call", "up", "rally", "gain", "breakout", 
            "accumulate", "accumulation", "growth", "support", "ath", "high",
            "upgrade", "higher", "positive", "bounce", "soar", "surges", "surge",
            "pump", "moon", "beat", "strong", "outperform", "success", "profit"
        ]
        
        self.bearish_keywords = [
            "bearish", "short", "sell", "put", "down", "dump", "crash", "loss",
            "breakdown", "fud", "regulation", "sec", "ban", "lawsuit", "fears",
            "drop", "plunge", "plummet", "fall", "lower", "negative", "resistance",
            "underperform", "downgrade", "weak", "liquidation", "liquidated", "scam"
        ]

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze a text string and return sentiment score and label.
        Score is from -1.0 (extremely bearish) to +1.0 (extremely bullish).
        """
        if not text:
            return {"score": 0.0, "label": "neutral", "bullish_words": 0, "bearish_words": 0}

        cleaned_text = re.sub(r"[^\w\s]", "", text.lower())
        words = cleaned_text.split()
        
        bullish_count = 0
        bearish_count = 0
        
        for word in words:
            if word in self.bullish_keywords:
                bullish_count += 1
            elif word in self.bearish_keywords:
                bearish_count += 1

        total_keywords = bullish_count + bearish_count
        if total_keywords == 0:
            return {"score": 0.0, "label": "neutral", "bullish_words": 0, "bearish_words": 0}
            
        score = (bullish_count - bearish_count) / total_keywords
        
        # Soften score based on density of keywords in text (up to 1.0)
        # e.g., if there's only 1 word, it shouldn't represent a full 1.0 sentiment for the whole block
        ratio = min(1.0, total_keywords / max(5.0, len(words) * 0.1))
        adjusted_score = score * ratio

        if adjusted_score >= 0.15:
            label = "bullish"
        elif adjusted_score <= -0.15:
            label = "bearish"
        else:
            label = "neutral"

        return {
            "score": round(float(adjusted_score), 3),
            "label": label,
            "bullish_words": bullish_count,
            "bearish_words": bearish_count
        }

    def get_batch_sentiment(self, texts: List[str]) -> Dict[str, Any]:
        """
        Calculate aggregate sentiment stats for a list of texts.
        """
        if not texts:
            return {"score": 0.0, "label": "neutral", "bullish_count": 0, "bearish_count": 0, "neutral_count": 0}

        scores = []
        bullish_c = 0
        bearish_c = 0
        neutral_c = 0

        for text in texts:
            res = self.analyze_text(text)
            scores.append(res["score"])
            if res["label"] == "bullish":
                bullish_c += 1
            elif res["label"] == "bearish":
                bearish_c += 1
            else:
                neutral_c += 1

        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        if avg_score >= 0.1:
            agg_label = "bullish"
        elif avg_score <= -0.1:
            agg_label = "bearish"
        else:
            agg_label = "neutral"

        return {
            "score": round(float(avg_score), 3),
            "label": agg_label,
            "bullish_count": bullish_c,
            "bearish_count": bearish_c,
            "neutral_count": neutral_c
        }

# Singleton
sentiment_analyzer = LexiconSentimentAnalyzer()

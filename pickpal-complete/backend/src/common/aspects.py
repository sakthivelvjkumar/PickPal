import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter

# Aspect keywords for different product categories
ASPECT_KEYWORDS = {
    "wireless_earbuds": {
        "sound_quality": ["sound", "audio", "music", "bass", "treble", "clarity", "crisp", "clear", "quality"],
        "noise_cancellation": ["noise", "cancellation", "anc", "isolation", "quiet", "cancel", "block"],
        "battery_life": ["battery", "charge", "charging", "life", "power", "hours", "duration"],
        "comfort": ["comfort", "fit", "comfortable", "ear", "pain", "hurt", "wear", "ergonomic"],
        "connectivity": ["connection", "bluetooth", "pairing", "connect", "disconnect", "stable", "drop"],
        "build_quality": ["build", "quality", "durable", "sturdy", "cheap", "plastic", "premium", "solid"],
        "price_value": ["price", "value", "money", "worth", "expensive", "cheap", "cost", "budget"],
        "call_quality": ["call", "microphone", "mic", "voice", "phone", "talk", "speaking"],
        "controls": ["control", "touch", "button", "gesture", "volume", "skip", "pause", "play"]
    },
    "standing_desk": {
        "stability": ["stable", "wobble", "shake", "sturdy", "solid", "firm", "rock", "steady"],
        "motor_quality": ["motor", "quiet", "smooth", "noise", "loud", "grinding", "operation"],
        "build_quality": ["build", "quality", "construction", "materials", "durable", "cheap", "premium"],
        "assembly": ["assembly", "setup", "install", "instructions", "parts", "tools", "easy", "difficult"],
        "height_range": ["height", "range", "adjust", "tall", "short", "position", "level"],
        "desktop_quality": ["desktop", "surface", "top", "scratch", "durable", "finish", "material"],
        "price_value": ["price", "value", "money", "worth", "expensive", "cheap", "cost", "budget"],
        "customer_service": ["service", "support", "help", "response", "warranty", "company"],
        "features": ["memory", "preset", "app", "smart", "programmable", "control", "panel"]
    },
    "laptop": {
        "performance": ["performance", "speed", "fast", "slow", "processor", "cpu", "ram", "memory"],
        "display": ["display", "screen", "monitor", "bright", "color", "resolution", "sharp", "crisp"],
        "battery_life": ["battery", "charge", "charging", "life", "power", "hours", "duration"],
        "build_quality": ["build", "quality", "construction", "durable", "cheap", "premium", "solid"],
        "keyboard": ["keyboard", "typing", "keys", "comfortable", "tactile", "responsive"],
        "trackpad": ["trackpad", "touchpad", "mouse", "cursor", "responsive", "smooth"],
        "ports": ["ports", "usb", "hdmi", "connectivity", "dongles", "adapters"],
        "price_value": ["price", "value", "money", "worth", "expensive", "cheap", "cost", "budget"],
        "weight": ["weight", "heavy", "light", "portable", "carry", "travel", "thin"]
    }
}

# Sentiment indicators for aspects
POSITIVE_INDICATORS = [
    "excellent", "amazing", "great", "good", "perfect", "love", "best", "fantastic", 
    "outstanding", "incredible", "wonderful", "awesome", "superb", "brilliant",
    "impressive", "solid", "reliable", "smooth", "comfortable", "easy", "clear"
]

NEGATIVE_INDICATORS = [
    "terrible", "awful", "bad", "worst", "hate", "horrible", "disappointing",
    "poor", "cheap", "flimsy", "uncomfortable", "difficult", "hard", "annoying",
    "frustrating", "issues", "problems", "broken", "defective", "useless"
]

def detect_product_category(product_name: str, query: str = "") -> str:
    """Detect product category from name and query."""
    text = f"{product_name} {query}".lower()
    
    category_indicators = {
        "wireless_earbuds": ["earbuds", "airpods", "headphones", "wireless", "bluetooth", "buds"],
        "standing_desk": ["desk", "standing", "sit-stand", "adjustable", "workstation"],
        "laptop": ["laptop", "macbook", "notebook", "computer", "thinkpad"]
    }
    
    for category, keywords in category_indicators.items():
        if any(keyword in text for keyword in keywords):
            return category
    
    return "general"

def extract_aspects_from_text(text: str, category: str = "general") -> Dict[str, List[str]]:
    """Extract aspect mentions from review text."""
    if category not in ASPECT_KEYWORDS:
        category = "general"
    
    text_lower = text.lower()
    sentences = re.split(r'[.!?]+', text)
    
    aspect_mentions = defaultdict(list)
    aspect_keywords = ASPECT_KEYWORDS.get(category, {})
    
    for sentence in sentences:
        sentence = sentence.strip().lower()
        if not sentence:
            continue
            
        for aspect, keywords in aspect_keywords.items():
            if any(keyword in sentence for keyword in keywords):
                aspect_mentions[aspect].append(sentence)
    
    return dict(aspect_mentions)

def calculate_aspect_sentiment(aspect_mentions: Dict[str, List[str]]) -> Dict[str, float]:
    """Calculate sentiment for each aspect based on mentions."""
    aspect_sentiments = {}
    
    for aspect, sentences in aspect_mentions.items():
        if not sentences:
            continue
            
        sentiment_scores = []
        for sentence in sentences:
            score = calculate_sentence_sentiment(sentence)
            sentiment_scores.append(score)
        
        # Average sentiment for this aspect
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        aspect_sentiments[aspect] = round(avg_sentiment, 3)
    
    return aspect_sentiments

def calculate_sentence_sentiment(sentence: str) -> float:
    """Calculate sentiment score for a sentence using keyword matching."""
    sentence_lower = sentence.lower()
    
    positive_count = sum(1 for word in POSITIVE_INDICATORS if word in sentence_lower)
    negative_count = sum(1 for word in NEGATIVE_INDICATORS if word in sentence_lower)
    
    # Simple sentiment calculation
    if positive_count == 0 and negative_count == 0:
        return 0.0  # Neutral
    
    sentiment = (positive_count - negative_count) / (positive_count + negative_count)
    return max(-1.0, min(1.0, sentiment))

def extract_pros_and_cons(reviews: List[Dict], category: str = "general") -> Tuple[List[str], List[str]]:
    """Extract pros and cons from reviews based on aspect analysis."""
    all_aspects = defaultdict(list)
    
    # Collect all aspect mentions
    for review in reviews:
        text = review.get("text", "")
        aspects = extract_aspects_from_text(text, category)
        
        for aspect, mentions in aspects.items():
            all_aspects[aspect].extend(mentions)
    
    # Calculate sentiment for each aspect
    aspect_sentiments = {}
    for aspect, mentions in all_aspects.items():
        aspect_sentiments[aspect] = calculate_aspect_sentiment({aspect: mentions})[aspect]
    
    # Generate pros and cons
    pros = []
    cons = []
    
    # Sort aspects by absolute sentiment strength
    sorted_aspects = sorted(aspect_sentiments.items(), key=lambda x: abs(x[1]), reverse=True)
    
    for aspect, sentiment in sorted_aspects[:6]:  # Top 6 aspects
        if sentiment > 0.2:  # Positive threshold
            pro_text = generate_aspect_summary(aspect, sentiment, positive=True)
            if pro_text:
                pros.append(pro_text)
        elif sentiment < -0.2:  # Negative threshold
            con_text = generate_aspect_summary(aspect, sentiment, positive=False)
            if con_text:
                cons.append(con_text)
    
    return pros[:3], cons[:3]  # Limit to top 3 each

def generate_aspect_summary(aspect: str, sentiment: float, positive: bool = True) -> str:
    """Generate human-readable summary for an aspect."""
    aspect_templates = {
        "sound_quality": {
            "positive": "Excellent sound quality with clear audio",
            "negative": "Poor sound quality and audio clarity"
        },
        "noise_cancellation": {
            "positive": "Effective noise cancellation",
            "negative": "Inadequate noise cancellation"
        },
        "battery_life": {
            "positive": "Long-lasting battery life",
            "negative": "Short battery life"
        },
        "comfort": {
            "positive": "Comfortable fit for extended use",
            "negative": "Uncomfortable fit causes discomfort"
        },
        "stability": {
            "positive": "Very stable with no wobbling",
            "negative": "Unstable with noticeable wobbling"
        },
        "build_quality": {
            "positive": "High-quality construction and materials",
            "negative": "Poor build quality and cheap materials"
        },
        "price_value": {
            "positive": "Great value for the price",
            "negative": "Overpriced for what you get"
        }
    }
    
    templates = aspect_templates.get(aspect, {
        "positive": f"Good {aspect.replace('_', ' ')}",
        "negative": f"Poor {aspect.replace('_', ' ')}"
    })
    
    return templates["positive"] if positive else templates["negative"]

def calculate_aspect_frequency(reviews: List[Dict], category: str = "general") -> Dict[str, int]:
    """Calculate how frequently each aspect is mentioned."""
    aspect_counts = Counter()
    
    for review in reviews:
        text = review.get("text", "")
        aspects = extract_aspects_from_text(text, category)
        
        for aspect in aspects.keys():
            aspect_counts[aspect] += 1
    
    return dict(aspect_counts)

def get_top_aspects(reviews: List[Dict], category: str = "general", top_n: int = 5) -> List[Tuple[str, int, float]]:
    """Get top aspects by frequency and average sentiment."""
    aspect_frequency = calculate_aspect_frequency(reviews, category)
    
    # Calculate average sentiment for each aspect
    all_aspects = defaultdict(list)
    for review in reviews:
        text = review.get("text", "")
        aspects = extract_aspects_from_text(text, category)
        for aspect, mentions in aspects.items():
            all_aspects[aspect].extend(mentions)
    
    aspect_results = []
    for aspect, frequency in aspect_frequency.items():
        if aspect in all_aspects:
            sentiment = calculate_aspect_sentiment({aspect: all_aspects[aspect]})[aspect]
            aspect_results.append((aspect, frequency, sentiment))
    
    # Sort by frequency first, then by absolute sentiment
    aspect_results.sort(key=lambda x: (x[1], abs(x[2])), reverse=True)
    
    return aspect_results[:top_n]

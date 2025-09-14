from typing import Dict, List, Optional
from datetime import datetime, timedelta
import math
import statistics

def calculate_composite_score(
    rating: float,
    sentiment: float,
    recency_days: float,
    helpfulness: float,
    weights: Dict[str, float] = None
) -> float:
    """Calculate composite score from multiple factors."""
    if weights is None:
        weights = {
            "rating": 0.4,
            "sentiment": 0.3,
            "recency": 0.2,
            "helpfulness": 0.1
        }
    
    # Normalize rating (0-5 scale to 0-10)
    rating_score = (rating / 5.0) * 10
    
    # Normalize sentiment (-1 to 1 scale to 0-10)
    sentiment_score = (sentiment + 1) * 5
    
    # Recency decay (exponential decay over 365 days)
    recency_score = 10 * math.exp(-recency_days / 180)  # Half-life of ~125 days
    
    # Helpfulness score (already 0-10 scale)
    helpfulness_score = min(helpfulness, 10)
    
    composite = (
        rating_score * weights["rating"] +
        sentiment_score * weights["sentiment"] +
        recency_score * weights["recency"] +
        helpfulness_score * weights["helpfulness"]
    )
    
    return round(composite, 2)

def calculate_z_scores(scores: List[float]) -> List[float]:
    """Calculate z-scores for normalization."""
    if len(scores) < 2:
        return [0.0] * len(scores)
    
    mean_score = statistics.mean(scores)
    std_score = statistics.stdev(scores)
    
    if std_score == 0:
        return [0.0] * len(scores)
    
    z_scores = [(score - mean_score) / std_score for score in scores]
    return z_scores

def apply_decay_factor(base_score: float, days_old: float, decay_rate: float = 0.1) -> float:
    """Apply exponential decay based on age."""
    decay_factor = math.exp(-decay_rate * days_old / 30)  # Monthly decay
    return base_score * decay_factor

def calculate_diversity_penalty(scores: List[float], diversity_threshold: float = 0.3) -> List[float]:
    """Apply penalty for lack of diversity in top results."""
    if len(scores) < 2:
        return scores
    
    # Calculate pairwise differences
    penalties = []
    for i, score in enumerate(scores):
        penalty = 0
        for j, other_score in enumerate(scores):
            if i != j:
                diff = abs(score - other_score)
                if diff < diversity_threshold:
                    penalty += (diversity_threshold - diff) * 0.1
        
        penalties.append(max(0, score - penalty))
    
    return penalties

def calculate_confidence_interval(scores: List[float], confidence: float = 0.95) -> tuple[float, float]:
    """Calculate confidence interval for scores."""
    if len(scores) < 2:
        return (0.0, 0.0)
    
    mean_score = statistics.mean(scores)
    std_score = statistics.stdev(scores)
    
    # Simple approximation without scipy
    # For 95% confidence, use t ≈ 2.0 for reasonable sample sizes
    t_value = 2.0 if confidence >= 0.95 else 1.65
    margin_error = t_value * (std_score / math.sqrt(len(scores)))
    
    return (mean_score - margin_error, mean_score + margin_error)

def normalize_scores_minmax(scores: List[float], target_min: float = 0, target_max: float = 10) -> List[float]:
    """Normalize scores using min-max scaling."""
    if not scores:
        return []
    
    min_score = min(scores)
    max_score = max(scores)
    
    if min_score == max_score:
        return [target_min] * len(scores)
    
    normalized = []
    for score in scores:
        norm_score = target_min + (score - min_score) * (target_max - target_min) / (max_score - min_score)
        normalized.append(round(norm_score, 2))
    
    return normalized

def calculate_review_quality_score(
    review_length: int,
    verified_purchase: bool,
    helpfulness_votes: int,
    total_votes: int
) -> float:
    """Calculate quality score for individual review."""
    # Length score (optimal around 100-300 characters)
    if review_length < 50:
        length_score = review_length / 50 * 5
    elif review_length <= 300:
        length_score = 10
    else:
        length_score = max(5, 10 - (review_length - 300) / 100)
    
    # Verification bonus
    verification_score = 10 if verified_purchase else 7
    
    # Helpfulness ratio
    if total_votes > 0:
        helpfulness_ratio = helpfulness_votes / total_votes
        helpfulness_score = helpfulness_ratio * 10
    else:
        helpfulness_score = 5  # Neutral for no votes
    
    # Weighted average
    quality_score = (
        length_score * 0.3 +
        verification_score * 0.4 +
        helpfulness_score * 0.3
    )
    
    return round(quality_score, 2)

def calculate_aspect_importance(
    aspect_frequency: Dict[str, int],
    total_reviews: int,
    user_weights: Dict[str, float] = None
) -> Dict[str, float]:
    """Calculate importance scores for different aspects."""
    if user_weights is None:
        user_weights = {}
    
    importance_scores = {}
    
    for aspect, frequency in aspect_frequency.items():
        # Base importance from frequency
        frequency_score = frequency / total_reviews
        
        # Apply user preference weights
        user_weight = user_weights.get(aspect, 1.0)
        
        # Calculate final importance
        importance = frequency_score * user_weight
        importance_scores[aspect] = round(importance, 3)
    
    return importance_scores

def rank_products_by_score(
    products: List[Dict],
    score_key: str = "score",
    diversity_factor: float = 0.1,
    max_results: int = 10
) -> List[Dict]:
    """Rank products by score with optional diversity consideration."""
    if not products:
        return []
    
    # Sort by score initially
    sorted_products = sorted(products, key=lambda x: x.get(score_key, 0), reverse=True)
    
    if diversity_factor > 0:
        # Apply diversity consideration
        scores = [p.get(score_key, 0) for p in sorted_products]
        adjusted_scores = calculate_diversity_penalty(scores, diversity_factor)
        
        # Re-sort with adjusted scores
        for i, product in enumerate(sorted_products):
            product["adjusted_score"] = adjusted_scores[i]
        
        sorted_products = sorted(sorted_products, key=lambda x: x.get("adjusted_score", 0), reverse=True)
    
    return sorted_products[:max_results]

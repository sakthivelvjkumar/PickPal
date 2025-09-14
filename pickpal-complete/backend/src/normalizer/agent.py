from typing import List, Dict
import hashlib
from rapidfuzz import fuzz
from datetime import datetime
from ..common.messages import *
from ..common.bus import AgentBase
from ..common.utils import logger, log_context, clean_text
from ..common.aspects import calculate_aspect_frequency

class NormalizerAgent(AgentBase):
    """Agent responsible for normalizing and enriching product candidates."""
    
    def __init__(self):
        super().__init__("normalizer")
    
    async def normalize_products(self, candidates: List[ProductCandidate]) -> List[EnrichedProduct]:
        """Normalize and enrich product candidates."""
        if not candidates:
            return []
        
        trace = self.create_trace(candidates[0].trace.request_id, "normalize")
        
        with log_context(trace.request_id):
            logger.info(f"Normalizing {len(candidates)} product candidates")
        
        # Deduplicate products
        deduplicated = self._deduplicate_products(candidates)
        
        # Enrich with signals and aspects
        enriched_products = []
        for candidate in deduplicated:
            enriched = await self._enrich_product(candidate, trace)
            enriched_products.append(enriched)
        
        with log_context(trace.request_id):
            logger.info(f"Normalization complete: {len(enriched_products)} enriched products")
            for product in enriched_products:
                signals_summary = {k: f"{v:.2f}" if isinstance(v, float) else v for k, v in product.signals.items()}
                logger.info(f"  - {product.name}: {len(product.aspect_frequencies)} aspects, signals: {signals_summary}")
        
        return enriched_products
    
    def _deduplicate_products(self, candidates: List[ProductCandidate]) -> List[ProductCandidate]:
        """Remove duplicate products using fuzzy matching."""
        if len(candidates) <= 1:
            return candidates
        
        unique_products = []
        seen_names = []
        
        for candidate in candidates:
            is_duplicate = False
            clean_name = clean_text(candidate.name)
            
            for seen_name in seen_names:
                similarity = fuzz.ratio(clean_name.lower(), seen_name.lower())
                if similarity > 85:  # 85% similarity threshold
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_products.append(candidate)
                seen_names.append(clean_name)
        
        return unique_products
    
    async def _enrich_product(self, candidate: ProductCandidate, trace: Trace) -> EnrichedProduct:
        """Enrich a product candidate with quality signals and aspects."""
        # Extract data from candidate
        reviews = candidate.raw_reviews
        
        # Calculate quality signals
        signals = self._calculate_signals(reviews)
        
        # Calculate aspect frequencies
        category = candidate.category or "general"
        aspect_counts = calculate_aspect_frequency(reviews, category)
        
        # Convert counts to frequencies (normalize by total reviews)
        total_reviews = len(reviews) if reviews else 1
        aspects = {aspect: count / total_reviews for aspect, count in aspect_counts.items()}
        
        return EnrichedProduct(
            trace=trace,
            canonical_id=self._generate_canonical_id(candidate.name),
            name=candidate.name,
            price=candidate.price,
            stars=candidate.stars,
            reviews_total=len(reviews),
            signals=signals,
            aspect_frequencies=aspects,
            raw_reviews=reviews
        )
    
    def _generate_canonical_id(self, product_name: str) -> str:
        """Generate a canonical ID for the product."""
        clean_name = clean_text(product_name).lower()
        return hashlib.md5(clean_name.encode()).hexdigest()[:12]
    
    def _calculate_signals(self, reviews: List[Dict]) -> Dict[str, float]:
        """Calculate quality signals from reviews."""
        if not reviews:
            return {}
        
        signals = {}
        
        # Verified purchase percentage
        verified_count = sum(1 for r in reviews if r.get("verified", False))
        signals["verified_pct"] = verified_count / len(reviews) if reviews else 0
        
        # Average helpfulness
        helpful_scores = []
        for review in reviews:
            helpful = review.get("helpful", 0)
            if helpful > 0:
                helpful_scores.append(min(helpful, 100))  # Cap at 100
        
        signals["avg_helpful"] = sum(helpful_scores) / len(helpful_scores) if helpful_scores else 0
        
        # Recency (days since median review)
        review_dates = []
        for review in reviews:
            date_str = review.get("date")
            if date_str:
                try:
                    review_date = datetime.strptime(date_str, "%Y-%m-%d")
                    days_ago = (datetime.now() - review_date).days
                    review_dates.append(days_ago)
                except ValueError:
                    continue
        
        if review_dates:
            review_dates.sort()
            median_idx = len(review_dates) // 2
            signals["recency_days_p50"] = review_dates[median_idx]
        else:
            signals["recency_days_p50"] = 365  # Default to 1 year
        
        # Review length distribution
        lengths = [len(r.get("text", "")) for r in reviews]
        if lengths:
            signals["avg_review_length"] = sum(lengths) / len(lengths)
            signals["review_length_std"] = (sum((l - signals["avg_review_length"]) ** 2 for l in lengths) / len(lengths)) ** 0.5
        else:
            signals["avg_review_length"] = 0
            signals["review_length_std"] = 0
        
        # Rating distribution
        ratings = [r.get("stars", 0) for r in reviews if r.get("stars")]
        if ratings:
            signals["rating_variance"] = sum((r - sum(ratings)/len(ratings)) ** 2 for r in ratings) / len(ratings)
        else:
            signals["rating_variance"] = 0
        
        return signals
    
    async def handle_normalize_request(self, message):
        """Handle normalize request from message bus."""
        try:
            candidates = message.payload["data"]
            response_topic = message.payload["response_topic"]
            
            enriched = await self.normalize_products(candidates)
            
            # Send response
            await self.send_message(response_topic, enriched, message.trace)
            
        except Exception as e:
            with log_context(message.trace.request_id):
                logger.error(f"Normalize request failed: {e}")
            raise

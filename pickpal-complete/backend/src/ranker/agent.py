from typing import List, Dict
import statistics
from ..common.messages import *
from ..common.bus import AgentBase
from ..common.utils import logger, log_context
from ..common.scoring import calculate_composite_score
from ..common.aspects import extract_pros_and_cons

class RankerAgent(AgentBase):
    """Agent responsible for ranking products and extracting pros/cons."""
    
    def __init__(self):
        super().__init__("ranker")
    
    async def rank_products(self, enriched: List[EnrichedProduct], weights: Dict[str, float] = None, topk: int = 3) -> RankedList:
        """Rank products and generate pros/cons."""
        if not enriched:
            return RankedList(trace=Trace(request_id="", step="rank", source_agent="ranker"), items=[])
        
        trace = self.create_trace(enriched[0].trace.request_id, "rank")
        
        with log_context(trace.request_id):
            logger.info(f"Ranking {len(enriched)} enriched products")
        
        if weights is None:
            weights = {
                "rating": 0.4,
                "sentiment": 0.3,
                "recency": 0.2,
                "helpfulness": 0.1
            }
        
        ranked_products = []
        
        for product in enriched:
            # Calculate composite score
            rating = product.stars or 0
            recency_days = product.signals.get("recency_days_p50", 365)
            helpfulness = product.signals.get("avg_helpful", 0)
            
            # Calculate overall sentiment from reviews
            sentiment = self._calculate_product_sentiment(product)
            
            score = calculate_composite_score(
                rating=rating,
                sentiment=sentiment,
                recency_days=recency_days,
                helpfulness=helpfulness,
                weights=weights
            )
            
            # Extract pros and cons from actual reviews
            reviews_data = [{"text": r.get("text", r.get("review", ""))} for r in product.raw_reviews if r.get("text") or r.get("review")]
            
            pros, cons = extract_pros_and_cons(reviews_data)
            
            # Only use fallbacks if no reviews found at all
            if not reviews_data:
                pros = ["Limited review data available"]
                cons = ["Insufficient review information"]
            elif not pros and not cons:
                # Reviews exist but no clear pros/cons extracted
                pros = ["Generally positive feedback"]
                cons = ["Minor issues reported"]
            
            why = {
                "rating_contribution": rating * weights["rating"],
                "sentiment_contribution": (sentiment + 1) * 5 * weights["sentiment"],
                "recency_contribution": 10 * (1 - min(recency_days / 365, 1)) * weights["recency"],
                "helpfulness_contribution": min(helpfulness / 10, 1) * 10 * weights["helpfulness"]
            }
            
            ranked_product = RankedProduct(
                trace=trace,
                canonical_id=product.canonical_id,
                name=product.name,
                score=score,
                pros=pros,
                cons=cons,
                why=why,
                price=product.price,
                stars=product.stars
            )
            
            ranked_products.append(ranked_product)
        
        # Sort by score
        ranked_products.sort(key=lambda x: x.score, reverse=True)
        
        # Apply diversity consideration (ensure variety in top results)
        if len(ranked_products) > 3:
            ranked_products = self._apply_diversity_filter(ranked_products)
        
        with log_context(trace.request_id):
            logger.info(f"Ranking complete: {len(ranked_products)} products scored")
            logger.info(f"Top score: {ranked_products[0].score:.2f} ({ranked_products[0].name})")
            logger.info(f"Score breakdown for top product:")
            top_why = ranked_products[0].why
            for component, value in top_why.items():
                logger.info(f"  - {component}: {value:.2f}")
            
            # Log pros/cons extraction results
            for i, product in enumerate(ranked_products[:3]):  # Top 3
                logger.info(f"Product {i+1} ({product.name}): {len(product.pros)} pros, {len(product.cons)} cons")
        
        return RankedList(
            trace=trace,
            items=ranked_products[:topk],
            total_scored=len(ranked_products),
            weights_used=weights
        )
    
    def _calculate_product_sentiment(self, product: EnrichedProduct) -> float:
        """Calculate overall sentiment for a product."""
        # This would normally use the raw_reviews, but since EnrichedProduct doesn't have them,
        # we'll estimate from signals and rating
        
        rating = product.stars or 0
        rating_variance = product.signals.get("rating_variance", 0)
        
        # Convert rating to sentiment scale (-1 to 1)
        base_sentiment = (rating - 3) / 2  # 5-star -> 1, 3-star -> 0, 1-star -> -1
        
        # Adjust for variance (high variance = mixed reviews = lower sentiment)
        variance_penalty = min(rating_variance / 2, 0.3)  # Cap penalty at 0.3
        
        final_sentiment = max(-1, min(1, base_sentiment - variance_penalty))
        
        return final_sentiment
    
    def _apply_diversity_filter(self, ranked_products: List[RankedProduct]) -> List[RankedProduct]:
        """Apply diversity filter to avoid too similar products in top results."""
        if len(ranked_products) <= 3:
            return ranked_products
        
        diverse_products = [ranked_products[0]]  # Always include top product
        
        for product in ranked_products[1:]:
            # Check if this product is too similar to already selected ones
            is_diverse = True
            
            for selected in diverse_products:
                # Simple diversity check based on price range
                if product.price and selected.price:
                    price_diff_pct = abs(product.price - selected.price) / max(product.price, selected.price)
                    if price_diff_pct < 0.15:  # Less than 15% price difference
                        score_diff = abs(product.score - selected.score)
                        if score_diff < 1.0:  # And similar scores
                            is_diverse = False
                            break
            
            if is_diverse:
                diverse_products.append(product)
            
            # Stop when we have enough diverse products
            if len(diverse_products) >= len(ranked_products):
                break
        
        return diverse_products
    
    async def handle_rank_request(self, message):
        """Handle rank request from message bus."""
        try:
            data = message.payload["data"]
            enriched = data["enriched"]
            weights = data.get("weights", {})
            response_topic = message.payload["response_topic"]
            
            ranked_list = await self.rank_products(enriched, weights)
            
            # Send response
            await self.send_message(response_topic, ranked_list, message.trace)
            
        except Exception as e:
            with log_context(message.trace.request_id):
                logger.error(f"Rank request failed: {e}")
            raise

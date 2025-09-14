import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
import hashlib
from dataclasses import dataclass

from .base_agent import BaseAgent, EventType
from models.schemas import Product, Review

@dataclass
class NormalizedProduct:
    product: Product
    normalized_brand: str
    normalized_price: float
    price_confidence: float
    duplicate_reviews_removed: int
    spam_score: float
    metadata_enriched: Dict[str, Any]

class NormalizationAgent(BaseAgent):
    def __init__(self, event_bus):
        super().__init__("normalization_agent", event_bus)
        
        # Brand normalization mapping
        self.brand_aliases = {
            'apple': ['apple', 'apple inc', 'apple inc.'],
            'sony': ['sony', 'sony corporation', 'sony corp'],
            'bose': ['bose', 'bose corporation', 'bose corp'],
            'samsung': ['samsung', 'samsung electronics', 'samsung galaxy'],
            'anker': ['anker', 'soundcore', 'soundcore by anker'],
            'sennheiser': ['sennheiser', 'sennheiser electronic'],
            'audio-technica': ['audio-technica', 'audio technica', 'ath'],
            'hyperx': ['hyperx', 'kingston hyperx'],
            'steelseries': ['steelseries', 'steel series'],
            'logitech': ['logitech', 'logitech g'],
            'razer': ['razer', 'razer inc']
        }
        
        # Spam detection patterns
        self.spam_patterns = [
            r'buy now',
            r'click here',
            r'amazing deal',
            r'limited time',
            r'\\u[0-9a-f]{4}',  # Unicode escape sequences
            r'(.)\1{4,}',  # Repeated characters
        ]
        
        # Aspect keywords for metadata enrichment
        self.aspect_keywords = {
            'battery_life': ['battery', 'playtime', 'listening time', 'charge', 'hours'],
            'comfort': ['comfort', 'comfortable', 'ergonomic', 'fit', 'padding'],
            'sound_quality': ['sound', 'audio', 'bass', 'treble', 'quality', 'clarity'],
            'noise_cancellation': ['noise cancel', 'anc', 'noise reduction', 'isolation'],
            'build_quality': ['build', 'sturdy', 'durable', 'material', 'construction'],
            'microphone': ['mic', 'microphone', 'calls', 'voice', 'recording'],
            'connectivity': ['bluetooth', 'wireless', 'connection', 'pairing', 'range'],
            'price_value': ['price', 'value', 'worth', 'expensive', 'cheap', 'affordable']
        }

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        products = task.get('products', [])
        reviews = task.get('reviews', [])
        
        await self.emit_event(EventType.TASK_STARTED, {
            'task': 'data_normalization',
            'products_count': len(products),
            'reviews_count': len(reviews)
        })
        
        try:
            # Normalize products
            normalized_products = []
            for product in products:
                normalized = await self._normalize_product(product, reviews)
                normalized_products.append(normalized)
            
            # Clean and enrich reviews
            clean_reviews = await self._clean_reviews(reviews)
            
            # Calculate aggregate metadata
            metadata = await self._calculate_aggregate_metadata(normalized_products, clean_reviews)
            
            result = {
                'normalized_products': normalized_products,
                'clean_reviews': clean_reviews,
                'metadata': metadata,
                'total_spam_removed': sum(p.duplicate_reviews_removed for p in normalized_products),
                'status': 'success'
            }
            
            await self.emit_event(EventType.TASK_COMPLETED, {
                'task': 'data_normalization',
                'products_processed': len(normalized_products),
                'reviews_cleaned': len(clean_reviews),
                'spam_removed': result['total_spam_removed']
            })
            
            return result
            
        except Exception as e:
            await self.emit_event(EventType.TASK_FAILED, {
                'task': 'data_normalization',
                'error': str(e)
            })
            raise

    async def _normalize_product(self, product: Product, all_reviews: List[Review]) -> NormalizedProduct:
        """Normalize a single product and its metadata"""
        
        # Normalize brand name
        normalized_brand = self._normalize_brand(product.brand)
        
        # Normalize price (handle different formats)
        normalized_price, price_confidence = self._normalize_price(product.price)
        
        # Get product reviews
        product_reviews = [r for r in all_reviews if r.product_id == product.product_id]
        
        # Remove duplicate reviews
        unique_reviews, duplicates_removed = await self._remove_duplicate_reviews(product_reviews)
        
        # Calculate spam score
        spam_score = await self._calculate_spam_score(unique_reviews)
        
        # Enrich metadata
        enriched_metadata = await self._enrich_metadata(product, unique_reviews)
        
        return NormalizedProduct(
            product=product,
            normalized_brand=normalized_brand,
            normalized_price=normalized_price,
            price_confidence=price_confidence,
            duplicate_reviews_removed=duplicates_removed,
            spam_score=spam_score,
            metadata_enriched=enriched_metadata
        )

    def _normalize_brand(self, brand: str) -> str:
        """Normalize brand name using alias mapping"""
        brand_lower = brand.lower().strip()
        
        for canonical_brand, aliases in self.brand_aliases.items():
            if brand_lower in aliases:
                return canonical_brand
        
        return brand_lower

    def _normalize_price(self, price: float) -> Tuple[float, float]:
        """Normalize price and return confidence score"""
        if price is None or price <= 0:
            return 0.0, 0.0
        
        # Basic price validation
        confidence = 1.0
        
        # Reduce confidence for unusual prices
        if price < 10 or price > 1000:
            confidence *= 0.8
        
        # Round to 2 decimal places
        normalized_price = round(price, 2)
        
        return normalized_price, confidence

    async def _remove_duplicate_reviews(self, reviews: List[Review]) -> Tuple[List[Review], int]:
        """Remove near-duplicate reviews using text similarity"""
        if len(reviews) <= 1:
            return reviews, 0
        
        unique_reviews = []
        review_hashes = set()
        duplicates_removed = 0
        
        for review in reviews:
            # Create a hash of normalized review text
            normalized_text = re.sub(r'\s+', ' ', review.text.lower().strip())
            text_hash = hashlib.md5(normalized_text.encode()).hexdigest()[:16]
            
            # Check for exact duplicates
            if text_hash in review_hashes:
                duplicates_removed += 1
                continue
            
            # Check for near-duplicates (simple similarity)
            is_duplicate = False
            for existing_review in unique_reviews:
                if self._calculate_text_similarity(review.text, existing_review.text) > 0.9:
                    duplicates_removed += 1
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_reviews.append(review)
                review_hashes.add(text_hash)
        
        return unique_reviews, duplicates_removed

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if len(words1) == 0 and len(words2) == 0:
            return 1.0
        if len(words1) == 0 or len(words2) == 0:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0

    async def _calculate_spam_score(self, reviews: List[Review]) -> float:
        """Calculate spam score for reviews (0 = no spam, 1 = all spam)"""
        if not reviews:
            return 0.0
        
        spam_indicators = 0
        total_checks = 0
        
        for review in reviews:
            # Check for spam patterns
            text_lower = review.text.lower()
            
            for pattern in self.spam_patterns:
                if re.search(pattern, text_lower):
                    spam_indicators += 1
                total_checks += 1
            
            # Check for repetitive phrases
            words = text_lower.split()
            if len(words) > 5:
                word_counts = Counter(words)
                most_common_word_count = word_counts.most_common(1)[0][1]
                if most_common_word_count > len(words) * 0.3:  # 30% repetition
                    spam_indicators += 1
                total_checks += 1
            
            # Check for extremely short or long reviews
            if len(review.text) < 10 or len(review.text) > 2000:
                spam_indicators += 0.5
            total_checks += 1
        
        return spam_indicators / max(total_checks, 1)

    async def _enrich_metadata(self, product: Product, reviews: List[Review]) -> Dict[str, Any]:
        """Enrich product metadata with aspect mentions and statistics"""
        
        # Count aspect mentions in reviews
        aspect_mentions = {}
        total_sentiment_by_aspect = {}
        
        for aspect, keywords in self.aspect_keywords.items():
            mentions = 0
            sentiment_sum = 0
            
            for review in reviews:
                text_lower = review.text.lower()
                for keyword in keywords:
                    if keyword in text_lower:
                        mentions += 1
                        # Simple sentiment: positive if rating >= 4, negative if <= 2
                        if review.rating >= 4:
                            sentiment_sum += 1
                        elif review.rating <= 2:
                            sentiment_sum -= 1
                        break  # Count each review only once per aspect
            
            aspect_mentions[aspect] = mentions
            total_sentiment_by_aspect[aspect] = sentiment_sum
        
        # Calculate review statistics
        review_stats = {
            'total_reviews': len(reviews),
            'verified_count': sum(1 for r in reviews if r.verified_purchase),
            'average_helpful_votes': sum(r.helpful_votes for r in reviews) / max(len(reviews), 1),
            'review_recency_score': self._calculate_recency_score(reviews),
            'rating_distribution': self._calculate_rating_distribution(reviews)
        }
        
        # Calculate aspect scores
        aspect_scores = {}
        for aspect, mentions in aspect_mentions.items():
            if mentions > 0:
                aspect_scores[aspect] = {
                    'mention_count': mentions,
                    'sentiment_score': total_sentiment_by_aspect[aspect] / mentions,
                    'relevance': mentions / len(reviews) if reviews else 0
                }
        
        return {
            'aspect_mentions': aspect_mentions,
            'aspect_scores': aspect_scores,
            'review_statistics': review_stats,
            'data_quality': {
                'price_confidence': 1.0,  # Will be set by the calling function
                'review_authenticity': 1.0 - (sum(1 for r in reviews if not r.verified_purchase) / max(len(reviews), 1)),
                'data_completeness': self._calculate_completeness_score(product)
            }
        }

    def _calculate_recency_score(self, reviews: List[Review]) -> float:
        """Calculate how recent the reviews are (1.0 = all very recent, 0.0 = all very old)"""
        if not reviews:
            return 0.0
        
        now = datetime.now()
        total_score = 0
        
        for review in reviews:
            days_old = (now - review.date).days
            # Exponential decay: 1.0 for today, 0.5 for 30 days, 0.1 for 90 days
            recency_score = max(0, 1.0 - (days_old / 90.0))
            total_score += recency_score
        
        return total_score / len(reviews)

    def _calculate_rating_distribution(self, reviews: List[Review]) -> Dict[int, int]:
        """Calculate distribution of ratings"""
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for review in reviews:
            rating = max(1, min(5, review.rating))  # Clamp to 1-5
            distribution[rating] += 1
        
        return distribution

    def _calculate_completeness_score(self, product: Product) -> float:
        """Calculate how complete the product data is"""
        score = 0.0
        total_fields = 7
        
        if product.name: score += 1
        if product.brand: score += 1
        if product.price > 0: score += 1
        if product.rating > 0: score += 1
        if product.url: score += 1
        if product.image_url: score += 1
        if product.sku or product.asin: score += 1
        
        return score / total_fields

    async def _clean_reviews(self, reviews: List[Review]) -> List[Review]:
        """Clean and filter reviews"""
        clean_reviews = []
        
        for review in reviews:
            # Skip extremely short reviews
            if len(review.text.strip()) < 10:
                continue
            
            # Skip reviews with too many spam indicators
            spam_score = await self._calculate_individual_review_spam_score(review)
            if spam_score > 0.7:
                continue
            
            clean_reviews.append(review)
        
        return clean_reviews

    async def _calculate_individual_review_spam_score(self, review: Review) -> float:
        """Calculate spam score for a single review"""
        spam_indicators = 0
        total_checks = 5
        
        text_lower = review.text.lower()
        
        # Check spam patterns
        for pattern in self.spam_patterns:
            if re.search(pattern, text_lower):
                spam_indicators += 1
                break
        
        # Check length
        if len(review.text) < 10 or len(review.text) > 2000:
            spam_indicators += 1
        
        # Check repetition
        words = text_lower.split()
        if len(words) > 3:
            word_counts = Counter(words)
            most_common_count = word_counts.most_common(1)[0][1]
            if most_common_count > len(words) * 0.4:
                spam_indicators += 1
        
        # Check for all caps
        if review.text.isupper() and len(review.text) > 20:
            spam_indicators += 1
        
        # Check helpful votes vs rating mismatch (suspicious if low rating but many helpful votes)
        if review.rating <= 2 and review.helpful_votes > 10:
            spam_indicators += 1
        
        return spam_indicators / total_checks

    async def _calculate_aggregate_metadata(self, products: List[NormalizedProduct], reviews: List[Review]) -> Dict[str, Any]:
        """Calculate aggregate metadata across all products"""
        
        total_products = len(products)
        total_reviews = len(reviews)
        
        # Brand distribution
        brand_counts = Counter(p.normalized_brand for p in products)
        
        # Price statistics
        prices = [p.normalized_price for p in products if p.normalized_price > 0]
        price_stats = {
            'min': min(prices) if prices else 0,
            'max': max(prices) if prices else 0,
            'avg': sum(prices) / len(prices) if prices else 0,
            'median': sorted(prices)[len(prices)//2] if prices else 0
        }
        
        # Quality metrics
        avg_spam_score = sum(p.spam_score for p in products) / max(total_products, 1)
        avg_duplicates_removed = sum(p.duplicate_reviews_removed for p in products) / max(total_products, 1)
        
        return {
            'total_products_processed': total_products,
            'total_reviews_processed': total_reviews,
            'brand_distribution': dict(brand_counts),
            'price_statistics': price_stats,
            'quality_metrics': {
                'average_spam_score': avg_spam_score,
                'average_duplicates_removed': avg_duplicates_removed,
                'data_quality_score': 1.0 - avg_spam_score
            }
        }

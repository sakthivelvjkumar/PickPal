import asyncio
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import Counter

from .base_agent import BaseAgent, EventType
from models.schemas import ProductScore, Product

class VerificationAgent(BaseAgent):
    def __init__(self, event_bus):
        super().__init__("verification_agent", event_bus)
        
        # Verification thresholds
        self.min_score_threshold = 40.0
        self.max_price_deviation = 0.15  # 15% price change tolerance
        self.review_bombing_threshold = 0.3  # 30% negative reviews in short time
        self.duplicate_similarity_threshold = 0.8
        
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        recommendations = task.get('recommendations', [])
        budget_max = task.get('inputs', {}).get('budget_max')
        min_products = task.get('inputs', {}).get('min_products', 3)
        
        await self.emit_event(EventType.TASK_STARTED, {
            'task': 'recommendation_verification',
            'recommendations_count': len(recommendations),
            'budget_max': budget_max
        })
        
        try:
            # Perform all verification checks
            verification_results = []
            verified_recommendations = []
            issues_found = []
            
            for i, product_score in enumerate(recommendations):
                result = await self._verify_recommendation(product_score, budget_max)
                verification_results.append(result)
                
                if result['passed_verification']:
                    verified_recommendations.append(product_score)
                else:
                    issues_found.extend(result['issues'])
            
            # Check diversity
            diversity_check = await self._check_diversity(verified_recommendations)
            if not diversity_check['passed']:
                issues_found.extend(diversity_check['issues'])
                # Remove duplicates to ensure diversity
                verified_recommendations = await self._ensure_diversity(verified_recommendations)
            
            # Check minimum count
            if len(verified_recommendations) < min_products:
                await self.emit_event(EventType.VERIFICATION_FAILED, {
                    'reason': 'insufficient_recommendations',
                    'count': len(verified_recommendations),
                    'required': min_products,
                    'issues': issues_found
                })
                
                # Trigger re-ranking or re-discovery
                return await self._handle_insufficient_recommendations(
                    verified_recommendations, min_products, issues_found
                )
            
            # Final ranking adjustment based on verification
            final_recommendations = await self._adjust_final_ranking(verified_recommendations)
            
            result = {
                'verified_recommendations': final_recommendations[:min_products],
                'verification_results': verification_results,
                'issues_found': issues_found,
                'total_passed': len(verified_recommendations),
                'diversity_ensured': diversity_check['passed'],
                'status': 'success'
            }
            
            await self.emit_event(EventType.TASK_COMPLETED, {
                'task': 'recommendation_verification',
                'verified_count': len(final_recommendations),
                'issues_count': len(issues_found)
            })
            
            return result
            
        except Exception as e:
            await self.emit_event(EventType.TASK_FAILED, {
                'task': 'recommendation_verification',
                'error': str(e)
            })
            raise

    async def _verify_recommendation(self, product_score: ProductScore, budget_max: Optional[float]) -> Dict[str, Any]:
        """Perform comprehensive verification on a single recommendation"""
        
        issues = []
        checks_passed = 0
        total_checks = 7
        
        product = product_score.product
        
        # 1. Link health check (simulated)
        link_healthy = await self._check_link_health(product.url)
        if link_healthy:
            checks_passed += 1
        else:
            issues.append(f"Product link appears broken: {product.name}")
        
        # 2. Price within budget
        if budget_max is not None:
            if product.price <= budget_max:
                checks_passed += 1
            else:
                issues.append(f"Price ${product.price} exceeds budget ${budget_max}: {product.name}")
        else:
            checks_passed += 1  # No budget constraint
        
        # 3. Stock status check
        stock_available = await self._check_stock_status(product)
        if stock_available:
            checks_passed += 1
        else:
            issues.append(f"Product appears to be out of stock: {product.name}")
        
        # 4. Review bombing detection
        review_bombing = await self._detect_review_bombing(product_score)
        if not review_bombing:
            checks_passed += 1
        else:
            issues.append(f"Potential review manipulation detected: {product.name}")
        
        # 5. Price reasonableness check
        price_reasonable = await self._check_price_reasonableness(product)
        if price_reasonable:
            checks_passed += 1
        else:
            issues.append(f"Price appears unreasonable for product category: {product.name}")
        
        # 6. Minimum quality score
        if product_score.overall_score >= self.min_score_threshold:
            checks_passed += 1
        else:
            issues.append(f"Overall score too low ({product_score.overall_score:.1f}): {product.name}")
        
        # 7. Confidence threshold
        if product_score.confidence >= 0.3:
            checks_passed += 1
        else:
            issues.append(f"Low confidence in scoring ({product_score.confidence:.2f}): {product.name}")
        
        verification_score = checks_passed / total_checks
        passed_verification = verification_score >= 0.7  # Need 70% of checks to pass
        
        return {
            'product_id': product.product_id,
            'product_name': product.name,
            'passed_verification': passed_verification,
            'verification_score': verification_score,
            'checks_passed': checks_passed,
            'total_checks': total_checks,
            'issues': issues,
            'details': {
                'link_healthy': link_healthy,
                'within_budget': budget_max is None or product.price <= budget_max,
                'in_stock': stock_available,
                'no_review_bombing': not review_bombing,
                'price_reasonable': price_reasonable,
                'meets_score_threshold': product_score.overall_score >= self.min_score_threshold,
                'sufficient_confidence': product_score.confidence >= 0.3
            }
        }

    async def _check_link_health(self, url: str) -> bool:
        """Check if product link is accessible (simulated for demo)"""
        # In real implementation, would make HTTP request
        # For demo, randomly simulate some broken links
        return random.random() > 0.05  # 95% links are healthy

    async def _check_stock_status(self, product: Product) -> bool:
        """Check product availability (simulated for demo)"""
        # In real implementation, would check retailer APIs
        # Use the in_stock field from product data
        return product.in_stock

    async def _detect_review_bombing(self, product_score: ProductScore) -> bool:
        """Detect potential review manipulation"""
        
        # Check for suspicious patterns in aspect scores
        aspect_scores = [score.score for score in product_score.aspect_scores]
        
        if not aspect_scores:
            return False
        
        # Check for extremely polarized scores (potential manipulation)
        very_high = sum(1 for score in aspect_scores if score > 90)
        very_low = sum(1 for score in aspect_scores if score < 20)
        total_aspects = len(aspect_scores)
        
        polarization_ratio = (very_high + very_low) / total_aspects
        
        # Check confidence levels (low confidence might indicate manipulation)
        avg_confidence = sum(score.confidence for score in product_score.aspect_scores) / total_aspects
        
        # Review bombing indicators
        bombing_score = 0
        
        if polarization_ratio > 0.6:  # More than 60% extreme scores
            bombing_score += 0.4
        
        if avg_confidence < 0.2:  # Very low confidence
            bombing_score += 0.3
        
        if product_score.overall_score > 85 and avg_confidence < 0.3:  # High score but low confidence
            bombing_score += 0.3
        
        return bombing_score > 0.5

    async def _check_price_reasonableness(self, product: Product) -> bool:
        """Check if price is reasonable for product category"""
        
        # Simple category-based price validation
        category_price_ranges = {
            'earbuds': (20, 400),
            'headphones': (30, 600),
            'gaming': (50, 300),
            'workout': (25, 200)
        }
        
        # Try to infer category from product name
        name_lower = product.name.lower()
        category = 'earbuds'  # default
        
        if any(word in name_lower for word in ['headphone', 'over-ear', 'on-ear']):
            category = 'headphones'
        elif any(word in name_lower for word in ['gaming', 'headset']):
            category = 'gaming'
        elif any(word in name_lower for word in ['sport', 'workout', 'fitness']):
            category = 'workout'
        
        min_price, max_price = category_price_ranges.get(category, (10, 1000))
        
        return min_price <= product.price <= max_price

    async def _check_diversity(self, recommendations: List[ProductScore]) -> Dict[str, Any]:
        """Check that recommendations offer diverse options"""
        
        if len(recommendations) < 2:
            return {'passed': True, 'issues': []}
        
        issues = []
        
        # Check brand diversity
        brands = [rec.product.brand for rec in recommendations]
        brand_counts = Counter(brands)
        
        if len(brand_counts) == 1 and len(recommendations) > 1:
            issues.append("All recommendations are from the same brand")
        
        # Check price diversity (should have options at different price points)
        prices = [rec.product.price for rec in recommendations]
        price_range = max(prices) - min(prices)
        avg_price = sum(prices) / len(prices)
        
        if price_range < avg_price * 0.3:  # Less than 30% price variation
            issues.append("Limited price diversity in recommendations")
        
        # Check that each recommendation has distinct strengths
        top_aspects = []
        for rec in recommendations:
            # Find the best aspect for this product
            best_aspect = max(rec.aspect_scores, key=lambda x: x.score)
            top_aspects.append(best_aspect.aspect)
        
        if len(set(top_aspects)) < len(recommendations) * 0.7:  # Less than 70% unique strengths
            issues.append("Recommendations don't offer sufficiently distinct trade-offs")
        
        # Check SKU uniqueness
        skus = [rec.product.sku or rec.product.product_id for rec in recommendations]
        if len(set(skus)) != len(skus):
            issues.append("Duplicate products in recommendations")
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'diversity_metrics': {
                'unique_brands': len(brand_counts),
                'price_range': price_range,
                'unique_strengths': len(set(top_aspects)),
                'unique_skus': len(set(skus))
            }
        }

    async def _ensure_diversity(self, recommendations: List[ProductScore]) -> List[ProductScore]:
        """Remove duplicates and ensure diversity"""
        
        diverse_recommendations = []
        seen_skus = set()
        seen_brands = set()
        
        # Sort by score first
        sorted_recs = sorted(recommendations, key=lambda x: x.overall_score, reverse=True)
        
        for rec in sorted_recs:
            sku = rec.product.sku or rec.product.product_id
            brand = rec.product.brand
            
            # Skip if we've seen this SKU
            if sku in seen_skus:
                continue
            
            # Prefer diversity in brands (but don't strictly enforce)
            if len(diverse_recommendations) < 3:
                diverse_recommendations.append(rec)
                seen_skus.add(sku)
                seen_brands.add(brand)
            elif brand not in seen_brands or len(seen_brands) >= 3:
                diverse_recommendations.append(rec)
                seen_skus.add(sku)
                seen_brands.add(brand)
        
        return diverse_recommendations

    async def _handle_insufficient_recommendations(self, verified_recs: List[ProductScore], min_required: int, issues: List[str]) -> Dict[str, Any]:
        """Handle case where we don't have enough verified recommendations"""
        
        # Emit replan event
        await self.emit_event(EventType.REPLAN_REQUIRED, {
            'reason': 'insufficient_verified_recommendations',
            'current_count': len(verified_recs),
            'required_count': min_required,
            'issues': issues
        })
        
        # For demo, relax some constraints and return what we have
        relaxed_recommendations = verified_recs
        
        # Add explanation for why recommendations are limited
        limitation_reason = "Limited recommendations due to strict quality filters"
        if any("budget" in issue.lower() for issue in issues):
            limitation_reason = "Limited options within specified budget"
        elif any("stock" in issue.lower() for issue in issues):
            limitation_reason = "Limited availability of recommended products"
        
        return {
            'verified_recommendations': relaxed_recommendations,
            'verification_results': [],
            'issues_found': issues,
            'total_passed': len(relaxed_recommendations),
            'diversity_ensured': True,
            'status': 'insufficient_evidence',
            'limitation_reason': limitation_reason,
            'recommendation': 'Consider relaxing budget or category constraints'
        }

    async def _adjust_final_ranking(self, verified_recommendations: List[ProductScore]) -> List[ProductScore]:
        """Final ranking adjustment based on verification results"""
        
        # Re-rank considering verification factors
        adjusted_recommendations = []
        
        for rec in verified_recommendations:
            # Create adjusted score considering verification factors
            adjustment_factor = 1.0
            
            # Boost for high confidence
            if rec.confidence > 0.8:
                adjustment_factor += 0.05
            
            # Boost for good price/value
            price_value_aspect = next((a for a in rec.aspect_scores if a.aspect == 'price_value'), None)
            if price_value_aspect and price_value_aspect.score > 75:
                adjustment_factor += 0.03
            
            # Boost for in-stock items
            if rec.product.in_stock:
                adjustment_factor += 0.02
            
            # Create adjusted copy
            adjusted_rec = ProductScore(
                product=rec.product,
                overall_score=rec.overall_score * adjustment_factor,
                aspect_scores=rec.aspect_scores,
                pros=rec.pros,
                cons=rec.cons,
                justification=rec.justification,
                confidence=rec.confidence
            )
            
            adjusted_recommendations.append(adjusted_rec)
        
        # Sort by adjusted scores
        return sorted(adjusted_recommendations, key=lambda x: x.overall_score, reverse=True)
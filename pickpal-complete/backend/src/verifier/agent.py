from typing import List, Dict
from ..common.messages import *
from ..common.bus import AgentBase
from ..common.utils import logger, log_context

class VerifierAgent(AgentBase):
    """Agent responsible for verifying ranked products against constraints."""
    
    def __init__(self):
        super().__init__("verifier")
    
    async def verify_products(self, ranked_list: RankedList, brief: ShoppingBrief) -> VerificationReport:
        """Verify ranked products against shopping brief constraints."""
        trace = self.create_trace(ranked_list.trace.request_id, "verify")
        self._current_request_id = trace.request_id
        
        with log_context(trace.request_id):
            logger.info(f"Starting verification of {len(ranked_list.items)} ranked products")
        
        checks = {}
        notes = []
        all_passed = True
        
        # Budget check
        budget_passed = self._check_budget(ranked_list.items, brief.constraints)
        checks["budget"] = budget_passed
        if not budget_passed:
            all_passed = False
            notes.append("Some products exceed budget constraints")
        
        # Out of stock check (mock - always passes for demo)
        oos_passed = self._check_out_of_stock(ranked_list.items)
        checks["out_of_stock"] = oos_passed
        if not oos_passed:
            all_passed = False
            notes.append("Some products are out of stock")
        
        # Duplicate check
        duplicate_passed = self._check_duplicates(ranked_list.items)
        checks["duplicates"] = duplicate_passed
        if not duplicate_passed:
            all_passed = False
            notes.append("Duplicate products found in results")
        
        # Evidence threshold check
        evidence_passed = self._check_evidence_threshold(ranked_list.items, brief.success)
        checks["evidence"] = evidence_passed
        if not evidence_passed:
            all_passed = False
            notes.append("Insufficient review evidence for some products")
        
        # Diversity check
        diversity_passed = self._check_diversity(ranked_list.items, brief.success)
        checks["diversity"] = diversity_passed
        if not diversity_passed:
            all_passed = False
            notes.append("Results lack sufficient diversity")
        
        with log_context(trace.request_id):
            logger.info(f"Verification result: {'PASSED' if all_passed else 'FAILED'}")
            if not all_passed:
                failed_checks = [k for k, v in checks.items() if not v]
                logger.info(f"Failed checks: {failed_checks}")
                for note in notes:
                    logger.info(f"  - {note}")
            
            # Log detailed verification results
            logger.info("Verification details:")
            for check_name, passed in checks.items():
                status = "✓" if passed else "✗"
                logger.info(f"  {status} {check_name}: {'PASS' if passed else 'FAIL'}")
        
        return VerificationReport(
            trace=trace,
            passed=all_passed,
            checks=checks,
            notes=notes
        )
    
    def _check_budget(self, products: List[RankedProduct], constraints: Dict) -> bool:
        """Check if products meet budget constraints."""
        if "max_price" not in constraints:
            return True
        
        max_price = constraints["max_price"]
        violations = []
        
        for product in products:
            if product.price > max_price:
                violations.append(f"{product.name} (${product.price}) > ${max_price}")
        
        if violations:
            with log_context(getattr(self, '_current_request_id', 'unknown')):
                logger.warning(f"Budget violations found: {len(violations)} products exceed max_price ${max_price}")
                for violation in violations:
                    logger.warning(f"  - {violation}")
            return False
        
        return True
    
    def _check_out_of_stock(self, products: List[RankedProduct]) -> bool:
        """Check if products are in stock (mock implementation)."""
        # Mock implementation - randomly mark some products as OOS for demo
        import random
        
        for product in products[:3]:
            # 10% chance of being out of stock
            if random.random() < 0.1:
                return False
        
        return True
    
    def _check_duplicates(self, products: List[RankedProduct]) -> bool:
        """Check for duplicate products in results."""
        seen_ids = set()
        
        for product in products:
            if product.canonical_id in seen_ids:
                return False
            seen_ids.add(product.canonical_id)
        
        return True
    
    def _check_evidence_threshold(self, products: List[RankedProduct], success_criteria: Dict) -> bool:
        """Check if products have sufficient review evidence."""
        min_reviews = success_criteria.get("min_reviews", 50)
        
        for product in products[:3]:  # Check top 3
            # We don't have review count in RankedProduct, so we'll estimate from score
            # In a real implementation, this would check actual review counts
            if product.score < 5.0:  # Assume low scores indicate insufficient evidence
                return False
        
        return True
    
    def _check_diversity(self, products: List[RankedProduct], success_criteria: Dict) -> bool:
        """Check if results have sufficient diversity."""
        diversity_required = success_criteria.get("diversity", True)
        if not diversity_required:
            return True
        
        if len(products) < 3:
            return len(products) >= 2  # Need at least 2 for diversity
        
        # Check price diversity in top 3
        top_3 = products[:3]
        prices = [p.price for p in top_3 if p.price]
        
        if len(prices) >= 2:
            price_range = max(prices) - min(prices)
            avg_price = sum(prices) / len(prices)
            
            # Require at least 20% price range relative to average
            if price_range / avg_price < 0.2:
                return False
        
        # Check score diversity
        scores = [p.score for p in top_3]
        if len(scores) >= 2:
            score_range = max(scores) - min(scores)
            # Require at least 1.0 point difference in scores
            if score_range < 1.0:
                return False
        
        return True
    
    async def handle_verify_request(self, message):
        """Handle verify request from message bus."""
        try:
            data = message.payload["data"]
            ranked_list = data["ranked_list"]
            brief = data["brief"]
            response_topic = message.payload["response_topic"]
            
            report = await self.verify_products(ranked_list, brief)
            
            # Send response
            await self.send_message(response_topic, report, message.trace)
            
        except Exception as e:
            with log_context(message.trace.request_id):
                logger.error(f"Verify request failed: {e}")
            raise

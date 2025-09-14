import time
from typing import List, Dict, Optional
from ..common.messages import *
from ..common.bus import AgentBase
from ..common.utils import logger, log_context, generate_request_id
from ..discovery.agent import DiscoveryAgent
from ..normalizer.agent import NormalizerAgent
from ..ranker.agent import RankerAgent
from ..verifier.agent import VerifierAgent
from ..clarifier.agent import ClarifierAgent

class PlannerAgent(AgentBase):
    """Main orchestrator agent that coordinates the entire shopping workflow."""
    
    def __init__(self):
        super().__init__("planner")
        
        # Initialize other agents
        self.discovery = DiscoveryAgent()
        self.normalizer = NormalizerAgent()
        self.ranker = RankerAgent()
        self.verifier = VerifierAgent()
        self.clarifier = ClarifierAgent()
    
    async def handle_user_goal(self, query: str, constraints: Dict = None, request_id: str = None) -> Dict:
        """Handle user shopping goal and orchestrate the entire pipeline."""
        if request_id is None:
            request_id = generate_request_id()
        
        trace = self.create_trace(request_id, "parse")
        
        with log_context(request_id):
            logger.info(f"Starting shopping pipeline for query: {query}")
        
        # Build initial shopping brief
        brief = self._build_shopping_brief(query, constraints or {}, trace)
        
        # Check if clarification is needed
        if await self.clarifier.should_clarify(brief):
            clarification_request = await self.clarifier.generate_clarification_request(brief)
            
            # For demo purposes, we'll simulate answers or skip clarification
            # In a real implementation, this would wait for user input
            with log_context(request_id):
                logger.info("Clarification needed but skipping for demo")
        
        # Discovery phase
        candidates = await self.discovery.discover_products(brief)
        
        if not candidates:
            with log_context(request_id):
                logger.warning("No candidates found")
            return {
                "success": False,
                "message": "No products found matching your criteria",
                "recommendations": []
            }
        
        # Normalization phase
        enriched = await self.normalizer.normalize_products(candidates)
        
        # Ranking phase
        ranked_list = await self.ranker.rank_products(enriched, brief.weights)
        
        # Verification phase
        verification_report = await self.verifier.verify_products(ranked_list, brief)
        
        # Handle verification failures with adaptation
        if not verification_report.passed:
            with log_context(request_id):
                logger.info("Verification failed, attempting adaptation")
            
            adapted_results = await self._adapt_and_retry(brief, candidates, enriched, ranked_list, verification_report)
            if adapted_results:
                ranked_list = adapted_results
        
        # Convert to final output format
        final_results = self._to_product_cards(ranked_list, request_id)
        
        with log_context(request_id):
            logger.info(f"Pipeline completed successfully with {len(final_results['recommendations'])} recommendations")
        
        return final_results
    
    def _build_shopping_brief(self, query: str, constraints: Dict, trace: Trace) -> ShoppingBrief:
        """Build shopping brief from user query and constraints."""
        # Parse category from query
        category = self._detect_category(query)
        
        # Extract use case from query
        use_case = self._extract_use_case(query)
        
        # Default weights
        weights = {
            "rating": 0.4,
            "sentiment": 0.3,
            "recency": 0.2,
            "helpfulness": 0.1
        }
        
        # Success criteria
        success = {
            "k": 3,
            "diversity": True,
            "min_reviews": 5  # Lowered for demo data
        }
        
        return ShoppingBrief(
            trace=trace,
            query=query,
            category=category,
            use_case=use_case,
            constraints=constraints,
            weights=weights,
            success=success
        )
    
    def _detect_category(self, query: str) -> Optional[str]:
        """Detect product category from query."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["earbuds", "headphones", "airpods", "wireless"]):
            return "wireless_earbuds"
        elif any(word in query_lower for word in ["desk", "standing", "sit-stand", "workstation"]):
            return "standing_desk"
        elif any(word in query_lower for word in ["laptop", "macbook", "notebook", "computer"]):
            return "laptop"
        
        return None
    
    def _extract_use_case(self, query: str) -> Optional[str]:
        """Extract use case from query."""
        query_lower = query.lower()
        
        use_cases = {
            "work": ["work", "office", "business", "professional"],
            "exercise": ["running", "gym", "workout", "exercise", "fitness"],
            "travel": ["travel", "commute", "commuting", "portable"],
            "gaming": ["gaming", "games", "game"],
            "music": ["music", "audio", "listening"],
            "calls": ["calls", "meetings", "phone", "conference"]
        }
        
        for use_case, keywords in use_cases.items():
            if any(keyword in query_lower for keyword in keywords):
                return use_case
        
        return None
    
    async def _adapt_and_retry(self, brief: ShoppingBrief, candidates: List[ProductCandidate], 
                              enriched: List[EnrichedProduct], ranked_list: RankedList, 
                              report: VerificationReport) -> Optional[RankedList]:
        """Adapt and retry when verification fails."""
        
        # Simple adaptation strategies
        if not report.checks.get("budget", True):
            # Relax budget constraint or find alternatives
            if "max_price" in brief.constraints:
                # Try removing the most expensive product and re-ranking
                filtered_enriched = [p for p in enriched if not p.price or p.price <= brief.constraints["max_price"]]
                if filtered_enriched:
                    return await self.ranker.rank_products(filtered_enriched, brief.weights)
        
        if not report.checks.get("evidence", True):
            # Lower evidence threshold
            brief.success["min_reviews"] = 1
            return await self.ranker.rank_products(enriched, brief.weights)
        
        if not report.checks.get("diversity", True):
            # Adjust ranking to promote diversity
            adjusted_weights = brief.weights.copy()
            adjusted_weights["rating"] = 0.3  # Reduce rating weight
            adjusted_weights["sentiment"] = 0.4  # Increase sentiment weight
            return await self.ranker.rank_products(enriched, adjusted_weights)
        
        return None
    
    def _to_product_cards(self, ranked_list: RankedList, request_id: str) -> Dict:
        """Convert ranked list to final product cards format."""
        recommendations = []
        
        for product in ranked_list.items[:3]:  # Top 3
            card = {
                "name": product.name,
                "price": product.price or 0.0,
                "rating": product.stars or 0.0,
                "overall_score": product.score,
                "pros": product.pros,
                "cons": product.cons,
                "summary": f"Scored {product.score:.1f}/10 based on comprehensive analysis",
                "review_count": len(getattr(product, 'raw_reviews', [])),
                "image_url": f"https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=300&h=300&fit=crop",
                "why": product.why
            }
            recommendations.append(card)
        
        return {
            "success": True,
            "query": ranked_list.items[0].trace.request_id if ranked_list.items else request_id,
            "recommendations": recommendations,
            "total_found": len(ranked_list.items),
            "request_id": request_id
        }

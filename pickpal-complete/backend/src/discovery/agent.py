from typing import List, Dict, Optional, Set
import json
import os
import asyncio
import aiohttp
import re
from urllib.parse import quote_plus, urljoin, urlparse
from datetime import datetime, timedelta
from ..common.messages import *
from ..common.bus import AgentBase
from ..common.utils import logger, log_context
from ..common.aspects import detect_product_category
from .helpers import deduplicate_candidates, gather_evidence_and_filter, expand_search_queries
from .adapters import AmazonAdapter, RedditAdapter, ReviewBlogAdapter

class DiscoveryAgent(AgentBase):
    """Agent responsible for discovering product candidates from various sources."""
    
    def __init__(self):
        super().__init__("discovery")
        self.mock_data = self._load_mock_data()
        self.session = None
        
        # Initialize adapters (will be set up when session is created)
        self.amazon_adapter = None
        self.reddit_adapter = None
        self.review_blog_adapter = None
        
        # Source priority configuration
        self.sources = {
            "amazon": {"priority": 1, "enabled": True, "timeout": 10},
            "reddit": {"priority": 2, "enabled": True, "timeout": 8},
            "review_blogs": {"priority": 3, "enabled": True, "timeout": 12},
            "mock_fallback": {"priority": 99, "enabled": True, "timeout": 1}
        }
        
        # Category-specific synonyms and search terms
        self.category_synonyms = {
            "wireless_earbuds": {
                "base_terms": ["wireless earbuds", "bluetooth earbuds", "true wireless"],
                "synonyms": {
                    "anc": ["noise cancelling", "active noise cancellation", "noise canceling"],
                    "sport": ["running", "workout", "fitness", "gym", "exercise"],
                    "earhooks": ["sport fit", "secure fit", "ear hooks", "stability"],
                    "waterproof": ["water resistant", "IPX", "sweat proof"]
                }
            },
            "standing_desk": {
                "base_terms": ["standing desk", "sit stand desk", "adjustable desk"],
                "synonyms": {
                    "electric": ["motorized", "powered", "automatic"],
                    "manual": ["hand crank", "mechanical", "adjustable height"],
                    "ergonomic": ["health", "posture", "wellness"]
                }
            }
        }
    
    def _load_mock_data(self) -> dict:
        """Load mock product data from JSON files."""
        mock_data = {}
        
        # Load earbuds data
        earbuds_path = os.path.join(os.path.dirname(__file__), "..", "common", "mocks", "reviews_earbuds.json")
        try:
            with open(earbuds_path, 'r') as f:
                earbuds_data = json.load(f)
                mock_data["wireless_earbuds"] = earbuds_data["products"]
        except FileNotFoundError:
            logger.warning(f"Mock data file not found: {earbuds_path}")
            mock_data["wireless_earbuds"] = []
        
        # Load desk data
        desks_path = os.path.join(os.path.dirname(__file__), "..", "common", "mocks", "reviews_desks.json")
        try:
            with open(desks_path, 'r') as f:
                desks_data = json.load(f)
                mock_data["standing_desk"] = desks_data["products"]
        except FileNotFoundError:
            logger.warning(f"Mock data file not found: {desks_path}")
            mock_data["standing_desk"] = []
        
        return mock_data
    
    async def discover_products(self, brief: ShoppingBrief) -> List[ProductCandidate]:
        """Discover product candidates from internet sources based on shopping brief."""
        trace = self.create_trace(brief.trace.request_id, "discovery")
        self._current_request_id = trace.request_id
        
        with log_context(trace.request_id):
            logger.info(f"Starting internet-based product discovery for query: {brief.query}")
        
        await self._ensure_session()
        
        try:
            # Step 1: Source selection & query building
            category = self._detect_category(brief.query, brief.category or "")
            search_queries = self._build_search_queries(brief, category)
            
            with log_context(trace.request_id):
                logger.info(f"Detected category: {category}")
                logger.info(f"Built {len(search_queries)} search queries: {search_queries}")
            
            # Step 2: Fetch from multiple sources with priority
            all_candidates = []
            sources_tried = []
            
            for source_name, config in sorted(self.sources.items(), key=lambda x: x[1]['priority']):
                if not config['enabled']:
                    continue
                    
                try:
                    with log_context(trace.request_id):
                        logger.info(f"Trying source: {source_name} (priority {config['priority']})")
                    
                    source_candidates = await self._fetch_from_source(
                        source_name, search_queries, category, brief, trace
                    )
                    
                    sources_tried.append({
                        'name': source_name,
                        'candidates_found': len(source_candidates),
                        'status': 'success'
                    })
                    
                    all_candidates.extend(source_candidates)
                    
                    with log_context(trace.request_id):
                        logger.info(f"Source {source_name}: found {len(source_candidates)} candidates")
                    
                except Exception as e:
                    sources_tried.append({
                        'name': source_name,
                        'candidates_found': 0,
                        'status': f'error: {str(e)[:100]}'
                    })
                    
                    with log_context(trace.request_id):
                        logger.warning(f"Source {source_name} failed: {e}")
            
            # Step 3: De-duplication at URL/name level
            deduplicated_candidates = deduplicate_candidates(all_candidates, trace.request_id)
            
            # Step 4: Evidence gathering & filtering
            filtered_candidates = gather_evidence_and_filter(
                deduplicated_candidates, brief, trace.request_id
            )
            
            # Step 5: Backoff & expansion if needed
            if len(filtered_candidates) < brief.success.get('k', 3):
                with log_context(trace.request_id):
                    logger.info(f"Only {len(filtered_candidates)} candidates found, attempting expansion")
                
                expanded_candidates = await self._expand_search(
                    brief, category, trace, current_candidates=filtered_candidates
                )
                filtered_candidates.extend(expanded_candidates)
            
            # Final constraint filtering
            final_candidates = self._filter_by_constraints(filtered_candidates, brief.constraints)
            
            # Log final results with sources
            with log_context(trace.request_id):
                logger.info(f"Discovery complete: {len(final_candidates)} candidates from {len(sources_tried)} sources")
                logger.info(f"Sources tried: {sources_tried}")
                
                for candidate in final_candidates:
                    source_info = candidate.meta.get('source', 'unknown')
                    logger.info(f"  - {candidate.name}: ${candidate.price}, {candidate.stars}★, "
                              f"{len(candidate.raw_reviews)} reviews (from {source_info})")
            
            return final_candidates
            
        except Exception as e:
            with log_context(trace.request_id):
                logger.error(f"Discovery failed, falling back to mock data: {e}")
            
            # Fallback to mock data
            return await self._fallback_to_mock_data(brief, category, trace)
    
    def _detect_category(self, query: str, category: str) -> str:
        # Detect product category
        detected_category = detect_product_category(query, category)
        if not detected_category or detected_category == "general":
            # Try to infer from query keywords
            query_lower = query.lower()
            if any(word in query_lower for word in ["earbuds", "headphones", "airpods"]):
                detected_category = "wireless_earbuds"
            elif any(word in query_lower for word in ["desk", "standing", "workstation"]):
                detected_category = "standing_desk"
            else:
                detected_category = "wireless_earbuds"  # Default fallback
        
        return detected_category
    
    def _build_search_queries(self, brief: ShoppingBrief, category: str) -> List[str]:
        """Build search queries with synonyms and constraints."""
        queries = []
        
        # Get base terms for category
        category_config = self.category_synonyms.get(category, {"base_terms": [brief.query]})
        base_terms = category_config.get("base_terms", [brief.query])
        
        # Extract use case and constraints from query
        query_lower = brief.query.lower()
        use_case_terms = []
        
        # Map use cases to search terms
        if "running" in query_lower or "sport" in query_lower:
            use_case_terms.extend(["running", "sport", "workout"])
        if "work" in query_lower or "office" in query_lower:
            use_case_terms.extend(["work", "office", "professional"])
        
        # Build queries combining base terms with use cases
        for base_term in base_terms:
            if use_case_terms:
                for use_case in use_case_terms[:2]:  # Limit to avoid too many queries
                    query = f"{base_term} {use_case}"
                    # Add price constraint to query for discovery (not filtering)
                    if "max_price" in brief.constraints:
                        query += f" under ${brief.constraints['max_price']}"
                    queries.append(query)
            else:
                query = base_term
                if "max_price" in brief.constraints:
                    query += f" under ${brief.constraints['max_price']}"
                queries.append(query)
        
        return queries[:5]  # Limit to 5 queries to avoid rate limits
    
    async def _ensure_session(self):
        """Ensure aiohttp session is available."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            
            # Initialize adapters with session
            # Get API keys from environment (optional)
            amazon_api_key = os.getenv('AMAZON_API_KEY')
            reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
            reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
            
            self.amazon_adapter = AmazonAdapter(self.session, amazon_api_key)
            self.reddit_adapter = RedditAdapter(self.session, reddit_client_id, reddit_client_secret)
            self.review_blog_adapter = ReviewBlogAdapter(self.session)
    
    async def _fetch_from_source(self, source_name: str, queries: List[str], category: str, 
                               brief: ShoppingBrief, trace: Trace) -> List[Dict]:
        """Fetch candidates from a specific source using real adapters."""
        try:
            if source_name == "amazon" and self.amazon_adapter:
                return await self.amazon_adapter.search_products(queries, category, max_results=20)
            elif source_name == "reddit" and self.reddit_adapter:
                return await self.reddit_adapter.search_products(queries, category, max_results=15)
            elif source_name == "review_blogs" and self.review_blog_adapter:
                return await self.review_blog_adapter.search_products(queries, category, max_results=10)
            elif source_name == "mock_fallback":
                return await self._fetch_from_mock_fallback(brief, category, trace)
            else:
                with log_context(trace.request_id):
                    logger.warning(f"Unknown or unavailable source: {source_name}")
                return []
        except Exception as e:
            with log_context(trace.request_id):
                logger.error(f"Error fetching from {source_name}: {str(e)}")
            return []
    
    
    
    
    async def _fetch_from_mock_fallback(self, brief: ShoppingBrief, category: str, trace: Trace) -> List[Dict]:
        """Fallback to mock data when other sources fail."""
        with log_context(trace.request_id):
            logger.info(f"Using mock fallback data for category: {category}")
        
        products_data = self.mock_data.get(category, [])
        mock_candidates = []
        
        for product in products_data:
            candidate = {
                "name": product.get("product", product.get("name", "Unknown Product")),
                "price": product.get("price", 0.0),
                "stars": product.get("stars", 0.0),
                "url": f"https://mock-source.com/product/{product.get('id', 'unknown')}",
                "reviews": product.get("reviews", []),
                "source": "mock_fallback",
                "last_updated": datetime.now().isoformat()
            }
            mock_candidates.append(candidate)
        
        return mock_candidates
    
    async def _expand_search(self, brief: ShoppingBrief, category: str, trace: Trace, 
                           current_candidates: List[Dict]) -> List[Dict]:
        """Expand search when insufficient candidates found."""
        expanded_candidates = []
        
        with log_context(trace.request_id):
            logger.info(f"Expanding search for category: {category}")
        
        # Generate broader search queries
        original_queries = self._build_search_queries(brief, category)
        expanded_queries = expand_search_queries(original_queries, category)
        
        with log_context(trace.request_id):
            logger.info(f"Expanded to {len(expanded_queries)} broader queries: {expanded_queries}")
        
        # Try sources again with expanded queries
        for source_name, config in sorted(self.sources.items(), key=lambda x: x[1]['priority']):
            if not config['enabled'] or source_name == "mock_fallback":
                continue
                
            try:
                source_candidates = await self._fetch_from_source(
                    source_name, expanded_queries, category, brief, trace
                )
                expanded_candidates.extend(source_candidates)
                
                with log_context(trace.request_id):
                    logger.info(f"Expansion - {source_name}: found {len(source_candidates)} additional candidates")
                    
            except Exception as e:
                with log_context(trace.request_id):
                    logger.warning(f"Expansion - {source_name} failed: {e}")
        
        # Remove duplicates against existing candidates
        existing_names = {c.get("name", "").lower() for c in current_candidates}
        unique_expanded = [c for c in expanded_candidates 
                          if c.get("name", "").lower() not in existing_names]
        
        with log_context(trace.request_id):
            logger.info(f"Expansion found {len(unique_expanded)} new unique candidates")
        
        return unique_expanded
    
    async def _fallback_to_mock_data(self, brief: ShoppingBrief, category: str, trace: Trace) -> List[ProductCandidate]:
        """Fallback to mock data when all internet sources fail."""
        with log_context(trace.request_id):
            logger.warning("All internet sources failed, falling back to mock data")
        
        mock_candidates = await self._fetch_from_mock_fallback(brief, category, trace)
        return self._filter_by_constraints(mock_candidates, brief.constraints)
    
    def _filter_by_constraints(self, candidates: List[Dict], constraints: Dict) -> List[ProductCandidate]:
        """Filter candidates based on constraints and convert to ProductCandidate objects."""
        filtered = []
        filtered_out = []
        
        for candidate in candidates:
            should_filter = False
            filter_reason = []
            
            # Price constraint
            if "max_price" in constraints:
                if candidate.get("price", 0) > constraints["max_price"]:
                    should_filter = True
                    filter_reason.append(f"price ${candidate.get('price', 0)} > max ${constraints['max_price']}")
            
            if "min_price" in constraints:
                if candidate.get("price", 0) < constraints["min_price"]:
                    should_filter = True
                    filter_reason.append(f"price ${candidate.get('price', 0)} < min ${constraints['min_price']}")
            
            # Rating constraint
            if "min_rating" in constraints:
                if candidate.get("stars", 0) < constraints["min_rating"]:
                    should_filter = True
                    filter_reason.append(f"rating {candidate.get('stars', 0)} < min {constraints['min_rating']}")
            
            # Review count constraint
            if "min_reviews" in constraints:
                review_count = candidate.get("reviews_count", len(candidate.get("reviews", [])))
                if review_count < constraints["min_reviews"]:
                    should_filter = True
                    filter_reason.append(f"reviews {review_count} < min {constraints['min_reviews']}")
            
            if should_filter:
                filtered_out.append({
                    "name": candidate.get("name", "Unknown"),
                    "price": candidate.get("price"),
                    "reason": "; ".join(filter_reason)
                })
            else:
                # Convert to ProductCandidate
                product_candidate = ProductCandidate(
                    trace=Trace(request_id=getattr(self, '_current_request_id', 'unknown'), 
                               step="filter", source_agent="discovery"),
                    name=candidate.get("name", "Unknown Product"),
                    price=candidate.get("price", 0.0),
                    stars=candidate.get("stars", 0.0),
                    category=candidate.get("category", "general"),
                    urls={"primary": candidate.get("url", "")},
                    raw_reviews=candidate.get("reviews", []),
                    meta={
                        "source": candidate.get("source", "unknown"),
                        "reviews_count": candidate.get("reviews_count", 0),
                        "last_updated": candidate.get("last_updated", ""),
                        "upvotes": candidate.get("upvotes", 0),
                        "mentions": candidate.get("mentions", 0),
                        "evidence_score": candidate.get("evidence_score", 0),
                        "evidence_notes": candidate.get("evidence_notes", [])
                    }
                )
                filtered.append(product_candidate)
        
        # Log filtering results
        with log_context(getattr(self, '_current_request_id', 'unknown')):
            logger.info(f"Constraint filtering: {len(filtered)} candidates passed, {len(filtered_out)} filtered out")
            for item in filtered_out:
                logger.info(f"Filtered out: {item['name']} (${item['price']}) - {item['reason']}")
        
        return filtered
    
    async def handle_discovery_request(self, message):
        """Handle discovery request from message bus."""
        try:
            brief = message.payload["data"]
            response_topic = message.payload["response_topic"]
            
            candidates = await self.discover_products(brief)
            
            # Send response
            await self.send_message(response_topic, candidates, message.trace)
            
        except Exception as e:
            with log_context(message.trace.request_id):
                logger.error(f"Discovery request failed: {e}")
            raise

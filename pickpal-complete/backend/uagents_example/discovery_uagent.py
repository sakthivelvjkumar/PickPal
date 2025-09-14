"""
Discovery uAgent - FetchAI/uAgents Framework Implementation
Converts the existing Discovery Agent to work with uAgents framework
"""

import asyncio
import aiohttp
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from uagents import Agent, Context, Protocol
from uagents.setup import fund_agent_if_low

# Message Models for uAgent Communication
class ShoppingBrief(BaseModel):
    request_id: str
    query: str
    category: Optional[str] = None
    use_case: Optional[str] = None
    constraints: Dict[str, float] = {}
    weights: Dict[str, float] = {}
    success: Dict[str, int] = {"k": 3, "min_reviews": 5}

class ProductCandidate(BaseModel):
    name: str
    price: Optional[float] = None
    stars: Optional[float] = None
    category: Optional[str] = None
    url: str = ""
    reviews: List[Dict] = []
    source: str = ""
    meta: Dict = {}

class DiscoveryResponse(BaseModel):
    request_id: str
    candidates: List[ProductCandidate]
    sources_tried: List[Dict]
    total_found: int
    success: bool = True
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    request_id: str
    error: str
    source_agent: str = "discovery"

# Create the Discovery Agent
discovery_agent = Agent(
    name="discovery_agent",
    port=8001,
    seed="discovery_agent_seed_phrase_unique_123",
    endpoint=["http://localhost:8001/submit"]
)

# Fund agent if needed (for testnet)
fund_agent_if_low(discovery_agent.wallet.address())

# Discovery Protocol
discovery_protocol = Protocol("ProductDiscovery", version="1.0")

# Agent state and configuration
class DiscoveryState:
    def __init__(self):
        self.session = None
        self.mock_data = {}
        self.sources = {
            "amazon": {"priority": 1, "enabled": True, "timeout": 10},
            "reddit": {"priority": 2, "enabled": True, "timeout": 8},
            "review_blogs": {"priority": 3, "enabled": True, "timeout": 12},
            "mock_fallback": {"priority": 99, "enabled": True, "timeout": 1}
        }
        self.category_synonyms = {
            "wireless_earbuds": ["earbuds", "wireless headphones", "bluetooth earbuds", "airpods"],
            "standing_desk": ["standing desk", "sit-stand desk", "adjustable desk", "height adjustable desk"],
            "laptop": ["laptop", "notebook", "macbook", "computer"]
        }

state = DiscoveryState()

@discovery_agent.on_event("startup")
async def setup_discovery_agent(ctx: Context):
    """Initialize the discovery agent on startup"""
    ctx.logger.info("Discovery Agent starting up...")
    
    # Initialize HTTP session
    state.session = aiohttp.ClientSession()
    
    # Load mock data
    try:
        mock_data_path = os.path.join(os.path.dirname(__file__), "mock_data.json")
        if os.path.exists(mock_data_path):
            with open(mock_data_path, 'r') as f:
                state.mock_data = json.load(f)
        else:
            # Create basic mock data
            state.mock_data = {
                "wireless_earbuds": [
                    {
                        "name": "Sony WF-1000XM4",
                        "price": 149.99,
                        "stars": 4.4,
                        "reviews": [
                            {"text": "Excellent noise cancellation", "stars": 5},
                            {"text": "Great battery life", "stars": 4}
                        ]
                    }
                ],
                "standing_desk": [
                    {
                        "name": "UPLIFT V2 Standing Desk",
                        "price": 599.99,
                        "stars": 4.6,
                        "reviews": [
                            {"text": "Sturdy and reliable", "stars": 5},
                            {"text": "Easy to assemble", "stars": 4}
                        ]
                    }
                ]
            }
    except Exception as e:
        ctx.logger.error(f"Failed to load mock data: {e}")
        state.mock_data = {}
    
    ctx.logger.info(f"Discovery Agent ready. Address: {discovery_agent.address}")

@discovery_agent.on_event("shutdown")
async def cleanup_discovery_agent(ctx: Context):
    """Cleanup on shutdown"""
    if state.session:
        await state.session.close()
    ctx.logger.info("Discovery Agent shutting down...")

@discovery_protocol.on_message(model=ShoppingBrief)
async def handle_discovery_request(ctx: Context, sender: str, msg: ShoppingBrief):
    """Handle product discovery requests"""
    ctx.logger.info(f"Received discovery request from {sender}: {msg.query}")
    
    try:
        # Perform discovery
        candidates, sources_tried = await discover_products(ctx, msg)
        
        # Send successful response
        response = DiscoveryResponse(
            request_id=msg.request_id,
            candidates=candidates,
            sources_tried=sources_tried,
            total_found=len(candidates),
            success=True
        )
        
        await ctx.send(sender, response)
        ctx.logger.info(f"Sent {len(candidates)} candidates to {sender}")
        
    except Exception as e:
        ctx.logger.error(f"Discovery failed: {str(e)}")
        
        # Send error response
        error_response = ErrorResponse(
            request_id=msg.request_id,
            error=str(e)
        )
        
        await ctx.send(sender, error_response)

async def discover_products(ctx: Context, brief: ShoppingBrief) -> tuple[List[ProductCandidate], List[Dict]]:
    """Main discovery logic adapted from original agent"""
    
    # Step 1: Detect category and build queries
    category = detect_category(brief.query)
    search_queries = build_search_queries(brief, category)
    
    ctx.logger.info(f"Category: {category}, Queries: {search_queries}")
    
    # Step 2: Fetch from multiple sources
    all_candidates = []
    sources_tried = []
    
    for source_name, config in sorted(state.sources.items(), key=lambda x: x[1]['priority']):
        if not config['enabled']:
            continue
            
        try:
            ctx.logger.info(f"Trying source: {source_name}")
            source_candidates = await fetch_from_source(ctx, source_name, search_queries, category, brief)
            
            all_candidates.extend(source_candidates)
            sources_tried.append({
                'name': source_name,
                'candidates_found': len(source_candidates),
                'status': 'success'
            })
            
            ctx.logger.info(f"Source {source_name}: found {len(source_candidates)} candidates")
            
        except Exception as e:
            sources_tried.append({
                'name': source_name,
                'candidates_found': 0,
                'status': f'error: {str(e)[:100]}'
            })
            ctx.logger.warning(f"Source {source_name} failed: {e}")
    
    # Step 3: Deduplication
    deduplicated_candidates = deduplicate_candidates(all_candidates)
    
    # Step 4: Evidence filtering
    filtered_candidates = gather_evidence_and_filter(deduplicated_candidates, brief)
    
    # Step 5: Convert to ProductCandidate objects
    final_candidates = []
    for candidate_dict in filtered_candidates:
        product_candidate = ProductCandidate(
            name=candidate_dict.get("name", "Unknown Product"),
            price=candidate_dict.get("price", 0.0),
            stars=candidate_dict.get("stars", 0.0),
            category=candidate_dict.get("category", "general"),
            url=candidate_dict.get("url", ""),
            reviews=candidate_dict.get("reviews", []),
            source=candidate_dict.get("source", "unknown"),
            meta=candidate_dict.get("meta", {})
        )
        final_candidates.append(product_candidate)
    
    return final_candidates, sources_tried

def detect_category(query: str) -> Optional[str]:
    """Detect product category from query"""
    query_lower = query.lower()
    
    for category, synonyms in state.category_synonyms.items():
        if any(synonym in query_lower for synonym in synonyms):
            return category
    
    return "general"

def build_search_queries(brief: ShoppingBrief, category: str) -> List[str]:
    """Build search queries with synonyms and constraints"""
    queries = []
    base_terms = [brief.query]
    
    # Add category synonyms
    if category in state.category_synonyms:
        base_terms.extend(state.category_synonyms[category][:2])  # Limit to 2 synonyms
    
    for base_term in base_terms:
        query = base_term
        if "max_price" in brief.constraints:
            query += f" under ${brief.constraints['max_price']}"
        queries.append(query)
    
    return queries[:3]  # Limit to 3 queries

async def fetch_from_source(ctx: Context, source_name: str, queries: List[str], 
                          category: str, brief: ShoppingBrief) -> List[Dict]:
    """Fetch candidates from a specific source"""
    
    if source_name == "mock_fallback":
        return await fetch_from_mock_fallback(ctx, brief, category)
    
    # For demo purposes, simulate other sources with mock data
    # In production, these would be real API calls
    candidates = []
    
    for query in queries:
        await asyncio.sleep(0.1)  # Simulate API delay
        
        if source_name == "amazon":
            mock_results = [
                {
                    "name": f"Premium {query.title()} Pro",
                    "price": 149.99,
                    "stars": 4.3,
                    "url": f"https://amazon.com/dp/MOCK{hash(query) % 1000}",
                    "reviews": [
                        {"text": "Great product!", "stars": 5},
                        {"text": "Good value", "stars": 4}
                    ],
                    "source": "amazon",
                    "category": category,
                    "last_updated": datetime.now().isoformat()
                }
            ]
            candidates.extend(mock_results)
            
        elif source_name == "reddit":
            mock_results = [
                {
                    "name": f"Reddit Recommended {query.title()}",
                    "price": 0.0,
                    "stars": 0.0,
                    "url": f"https://reddit.com/r/BuyItForLife/comments/mock{hash(query) % 1000}",
                    "reviews": [
                        {"text": f"Great {query}, highly recommended!", "stars": 0}
                    ],
                    "source": "reddit",
                    "upvotes": 156,
                    "mentions": 23,
                    "category": category,
                    "last_updated": datetime.now().isoformat()
                }
            ]
            candidates.extend(mock_results)
    
    return candidates

async def fetch_from_mock_fallback(ctx: Context, brief: ShoppingBrief, category: str) -> List[Dict]:
    """Fallback to mock data when other sources fail"""
    ctx.logger.info(f"Using mock fallback data for category: {category}")
    
    products_data = state.mock_data.get(category, [])
    mock_candidates = []
    
    for product in products_data:
        candidate = {
            "name": product.get("name", "Unknown Product"),
            "price": product.get("price", 0.0),
            "stars": product.get("stars", 0.0),
            "url": f"https://mock-source.com/product/{product.get('id', 'unknown')}",
            "reviews": product.get("reviews", []),
            "source": "mock_fallback",
            "category": category,
            "last_updated": datetime.now().isoformat()
        }
        mock_candidates.append(candidate)
    
    return mock_candidates

def deduplicate_candidates(candidates: List[Dict]) -> List[Dict]:
    """Remove duplicate candidates based on name similarity"""
    if not candidates:
        return []
    
    unique_candidates = []
    seen_names = []
    
    for candidate in candidates:
        name = candidate.get("name", "").lower().strip()
        is_duplicate = False
        
        for seen_name in seen_names:
            # Simple similarity check (could use more sophisticated matching)
            if name == seen_name or (len(name) > 10 and name in seen_name) or (len(seen_name) > 10 and seen_name in name):
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_candidates.append(candidate)
            seen_names.append(name)
    
    return unique_candidates

def gather_evidence_and_filter(candidates: List[Dict], brief: ShoppingBrief) -> List[Dict]:
    """Filter candidates based on evidence quality"""
    filtered_candidates = []
    min_reviews = brief.success.get("min_reviews", 5)
    
    for candidate in candidates:
        evidence_score = 0
        evidence_notes = []
        
        # Review count evidence
        reviews_count = len(candidate.get("reviews", []))
        if reviews_count >= min_reviews:
            evidence_score += 2
            evidence_notes.append(f"{reviews_count} reviews")
        elif reviews_count > 0:
            evidence_score += 1
            evidence_notes.append(f"only {reviews_count} reviews")
        
        # Source credibility
        source = candidate.get("source", "")
        if source == "amazon":
            evidence_score += 2
            evidence_notes.append("Amazon verified")
        elif source == "reddit":
            evidence_score += 1
            evidence_notes.append("Reddit discussion")
        
        # Accept candidates with sufficient evidence
        if evidence_score >= 1:  # Lowered threshold for demo
            candidate["evidence_score"] = evidence_score
            candidate["evidence_notes"] = evidence_notes
            filtered_candidates.append(candidate)
    
    return filtered_candidates

# Include the protocol in the agent
discovery_agent.include(discovery_protocol)

if __name__ == "__main__":
    print(f"Starting Discovery Agent...")
    print(f"Agent address: {discovery_agent.address}")
    discovery_agent.run()

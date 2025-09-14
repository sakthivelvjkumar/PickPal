"""
MyPickPal Discovery Agent - Agentverse Compatible
Converts the existing Discovery Agent to work with Agentverse marketplace
"""

import asyncio
import uuid
from typing import Dict, List, Any
from pydantic import BaseModel, Field

from uagents import Agent, Context, Protocol
from uagents.setup import fund_agent_if_low

# Import existing discovery logic
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from discovery.agent import DiscoveryAgent as CoreDiscoveryAgent
from common.messages import ProductCandidate, ShoppingBrief

# Agentverse-compatible message models
class AgentverseShoppingRequest(BaseModel):
    """Shopping request compatible with Agentverse Chat Protocol"""
    request_id: str = Field(description="Unique request identifier")
    user_query: str = Field(description="Natural language shopping query")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Shopping constraints")
    user_address: str = Field(description="Address of requesting user/agent")

class AgentverseDiscoveryResponse(BaseModel):
    """Discovery response for Agentverse"""
    request_id: str = Field(description="Request identifier")
    success: bool = Field(description="Whether discovery was successful")
    products_found: int = Field(description="Number of products discovered")
    products: List[Dict[str, Any]] = Field(description="Discovered product candidates")
    sources_used: List[str] = Field(description="Sources that were queried")
    execution_time_ms: int = Field(description="Time taken for discovery")
    message: str = Field(description="Human-readable status message")

# Create Agentverse-compatible agent
discovery_agent = Agent(
    name="MyPickPal-Discovery",
    seed="mypickpal_discovery_agentverse_seed_12345",
    port=8000,
    endpoint=["http://localhost:8000/submit"]
)

# Initialize core discovery logic
core_discovery = CoreDiscoveryAgent()

# Agentverse Discovery Protocol
discovery_protocol = Protocol("MyPickPal-Discovery", version="1.0")

@discovery_agent.on_event("startup")
async def setup_agentverse_discovery(ctx: Context):
    """Initialize discovery agent for Agentverse"""
    ctx.logger.info("MyPickPal Discovery Agent starting for Agentverse...")
    ctx.logger.info(f"Agent address: {discovery_agent.address}")
    ctx.logger.info(f"Wallet address: {discovery_agent.wallet.address()}")
    
    # Fund agent if needed
    try:
        await fund_agent_if_low(discovery_agent.wallet.address())
        ctx.logger.info("Agent funded successfully")
    except Exception as e:
        ctx.logger.warning(f"Could not auto-fund agent: {e}")
    
    # Initialize core discovery components
    await core_discovery.initialize()
    ctx.logger.info("Core discovery system initialized")
    
    # Log service capabilities for Agentverse
    ctx.logger.info("Available services:")
    ctx.logger.info("- Product Discovery: Find products from Amazon, Reddit, Review Blogs")
    ctx.logger.info("- Multi-source Search: Prioritized source selection with fallback")
    ctx.logger.info("- Evidence Filtering: Quality-based product filtering")
    ctx.logger.info("- Deduplication: Remove duplicate products across sources")

@discovery_protocol.on_message(model=AgentverseShoppingRequest)
async def handle_discovery_request(ctx: Context, sender: str, msg: AgentverseShoppingRequest):
    """Handle product discovery requests from Agentverse"""
    start_time = asyncio.get_event_loop().time()
    
    ctx.logger.info(f"Received discovery request {msg.request_id} from {sender}")
    ctx.logger.info(f"Query: {msg.user_query}")
    ctx.logger.info(f"Constraints: {msg.constraints}")
    
    try:
        # Convert to internal format
        shopping_brief = ShoppingBrief(
            request_id=msg.request_id,
            query=msg.user_query,
            category="general",  # Will be detected by core agent
            use_case="general",
            constraints=msg.constraints,
            weights={"rating": 0.4, "sentiment": 0.3, "recency": 0.2, "helpfulness": 0.1},
            success={"k": 5, "diversity": True, "min_reviews": 3}
        )
        
        # Perform discovery using core logic
        ctx.logger.info("Starting product discovery...")
        candidates = await core_discovery.discover_products(shopping_brief)
        
        # Calculate execution time
        execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Convert candidates to Agentverse format
        products_data = []
        sources_used = set()
        
        for candidate in candidates:
            product_dict = {
                "name": candidate.name,
                "price": candidate.price,
                "rating": candidate.rating,
                "url": candidate.url,
                "source": candidate.source,
                "review_count": len(candidate.raw_reviews),
                "description": candidate.description or "No description available",
                "image_url": candidate.image_url,
                "availability": candidate.availability
            }
            products_data.append(product_dict)
            sources_used.add(candidate.source)
        
        # Create response
        response = AgentverseDiscoveryResponse(
            request_id=msg.request_id,
            success=True,
            products_found=len(candidates),
            products=products_data,
            sources_used=list(sources_used),
            execution_time_ms=execution_time,
            message=f"Successfully discovered {len(candidates)} products from {len(sources_used)} sources"
        )
        
        ctx.logger.info(f"Discovery completed: {len(candidates)} products found in {execution_time}ms")
        
        # Send response back to requester
        await ctx.send(sender, response)
        
    except Exception as e:
        ctx.logger.error(f"Discovery failed for request {msg.request_id}: {e}")
        
        # Send error response
        error_response = AgentverseDiscoveryResponse(
            request_id=msg.request_id,
            success=False,
            products_found=0,
            products=[],
            sources_used=[],
            execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
            message=f"Discovery failed: {str(e)}"
        )
        
        await ctx.send(sender, error_response)

# Chat Protocol for ASI:One integration
chat_protocol = Protocol("Chat", version="1.0")

class ChatMessage(BaseModel):
    """Chat message for ASI:One integration"""
    message: str = Field(description="User message")
    session_id: str = Field(description="Chat session identifier")

class ChatResponse(BaseModel):
    """Chat response for ASI:One"""
    message: str = Field(description="Agent response")
    session_id: str = Field(description="Chat session identifier")
    action_taken: bool = Field(description="Whether an action was performed")
    products_found: int = Field(default=0, description="Number of products found if search performed")

@chat_protocol.on_message(model=ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """Handle chat messages from ASI:One"""
    ctx.logger.info(f"Chat message from {sender}: {msg.message}")
    
    # Simple intent detection for shopping queries
    shopping_keywords = ["find", "search", "buy", "purchase", "recommend", "best", "cheap", "under", "$"]
    is_shopping_query = any(keyword in msg.message.lower() for keyword in shopping_keywords)
    
    if is_shopping_query:
        # Convert chat to shopping request
        request_id = f"chat_{msg.session_id}_{uuid.uuid4().hex[:8]}"
        
        # Extract constraints from natural language (simple parsing)
        constraints = {}
        words = msg.message.lower().split()
        
        # Extract price constraints
        for i, word in enumerate(words):
            if word == "under" and i + 1 < len(words):
                next_word = words[i + 1].replace("$", "").replace(",", "")
                try:
                    constraints["max_price"] = float(next_word)
                except ValueError:
                    pass
        
        shopping_request = AgentverseShoppingRequest(
            request_id=request_id,
            user_query=msg.message,
            constraints=constraints,
            user_address=sender
        )
        
        # Process the shopping request
        await handle_discovery_request(ctx, sender, shopping_request)
        
        # Send chat response
        chat_response = ChatResponse(
            message=f"I'm searching for products based on: '{msg.message}'. Let me find the best options for you!",
            session_id=msg.session_id,
            action_taken=True,
            products_found=0  # Will be updated when discovery completes
        )
        
    else:
        # General chat response
        chat_response = ChatResponse(
            message="I'm MyPickPal's Discovery Agent! I can help you find products. Try asking me to 'find wireless earbuds under $100' or 'recommend a gaming laptop'.",
            session_id=msg.session_id,
            action_taken=False
        )
    
    await ctx.send(sender, chat_response)

# Include protocols
discovery_agent.include(discovery_protocol)
discovery_agent.include(chat_protocol)

if __name__ == "__main__":
    print("Starting MyPickPal Discovery Agent for Agentverse...")
    print(f"Agent address: {discovery_agent.address}")
    print("Services available:")
    print("- Product Discovery (Amazon, Reddit, Review Blogs)")
    print("- Natural Language Shopping Queries")
    print("- Chat Protocol for ASI:One")
    print("- Multi-source Search with Evidence Filtering")
    discovery_agent.run()

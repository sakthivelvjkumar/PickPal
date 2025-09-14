"""
Planner uAgent - FetchAI/uAgents Framework Implementation
Main orchestrator that coordinates the shopping pipeline using uAgents
"""

import asyncio
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from uagents import Agent, Context, Protocol
from uagents.setup import fund_agent_if_low

# Import message models
from discovery_uagent import ShoppingBrief, DiscoveryResponse, ErrorResponse

# Additional message models for orchestration
class ShoppingRequest(BaseModel):
    request_id: str
    query: str
    constraints: Dict[str, float] = {}
    user_address: str

class NormalizationRequest(BaseModel):
    request_id: str
    candidates: List[Dict]

class RankingRequest(BaseModel):
    request_id: str
    enriched_products: List[Dict]
    weights: Dict[str, float] = {}

class FinalResponse(BaseModel):
    request_id: str
    success: bool
    recommendations: List[Dict] = []
    total_found: int = 0
    message: str = ""

# Create the Planner Agent
planner_agent = Agent(
    name="planner_agent",
    port=8000,
    seed="planner_agent_seed_phrase_unique_456",
    endpoint=["http://localhost:8000/submit"]
)

fund_agent_if_low(planner_agent.wallet.address())

# Planner Protocol
planner_protocol = Protocol("ShoppingOrchestration", version="1.0")

# Agent addresses (in production, these would be discovered via agent registry)
AGENT_ADDRESSES = {
    "discovery": "agent1qw8s7d9k2j3h4g5f6d7s8a9z0x1c2v3b4n5m6",  # Mock address
    "normalizer": "agent1qx7r8e0l3k4j5h6g7f8d9s0a1z2x3c4v5b6n7",  # Mock address
    "ranker": "agent1qy6q9r1m4l5k6j7h8g9f0d1s2a3z4x5c6v7b8",     # Mock address
    "verifier": "agent1qz5p0t2n5m6l7k8j9h0g1f2d3s4a5z6x7c8v9"    # Mock address
}

# Request state management
class RequestState:
    def __init__(self):
        self.requests = {}  # request_id -> request_data
        self.timeouts = {}  # request_id -> timeout_task

request_state = RequestState()

@planner_agent.on_event("startup")
async def setup_planner_agent(ctx: Context):
    """Initialize the planner agent"""
    ctx.logger.info("Planner Agent starting up...")
    ctx.logger.info(f"Agent address: {planner_agent.address}")
    
    # Start cleanup task for expired requests
    asyncio.create_task(cleanup_expired_requests(ctx))

async def cleanup_expired_requests(ctx: Context):
    """Cleanup expired requests periodically"""
    while True:
        try:
            current_time = datetime.now()
            expired_requests = []
            
            for request_id, request_data in request_state.requests.items():
                if current_time - request_data.get("created_at", current_time) > timedelta(minutes=5):
                    expired_requests.append(request_id)
            
            for request_id in expired_requests:
                if request_id in request_state.requests:
                    del request_state.requests[request_id]
                if request_id in request_state.timeouts:
                    request_state.timeouts[request_id].cancel()
                    del request_state.timeouts[request_id]
                    
                ctx.logger.info(f"Cleaned up expired request: {request_id}")
            
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            ctx.logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60)

@planner_protocol.on_message(model=ShoppingRequest)
async def handle_shopping_request(ctx: Context, sender: str, msg: ShoppingRequest):
    """Handle incoming shopping requests from users"""
    ctx.logger.info(f"Received shopping request from {sender}: {msg.query}")
    
    # Store request state
    request_state.requests[msg.request_id] = {
        "user_address": sender,
        "stage": "discovery",
        "query": msg.query,
        "constraints": msg.constraints,
        "created_at": datetime.now(),
        "stages_completed": []
    }
    
    # Build shopping brief
    brief = build_shopping_brief(msg.query, msg.constraints, msg.request_id)
    
    try:
        # Send to Discovery Agent
        await ctx.send(AGENT_ADDRESSES["discovery"], brief)
        ctx.logger.info(f"Sent discovery request for {msg.request_id}")
        
        # Set timeout for discovery
        timeout_task = asyncio.create_task(
            handle_request_timeout(ctx, msg.request_id, "discovery", 30)
        )
        request_state.timeouts[msg.request_id] = timeout_task
        
    except Exception as e:
        ctx.logger.error(f"Failed to send discovery request: {e}")
        
        # Send error response to user
        error_response = FinalResponse(
            request_id=msg.request_id,
            success=False,
            message=f"Failed to start product discovery: {str(e)}"
        )
        await ctx.send(sender, error_response)

@planner_protocol.on_message(model=DiscoveryResponse)
async def handle_discovery_response(ctx: Context, sender: str, msg: DiscoveryResponse):
    """Handle discovery results"""
    ctx.logger.info(f"Received discovery response for {msg.request_id}: {msg.total_found} candidates")
    
    if msg.request_id not in request_state.requests:
        ctx.logger.warning(f"Received response for unknown request: {msg.request_id}")
        return
    
    request_data = request_state.requests[msg.request_id]
    
    # Cancel timeout
    if msg.request_id in request_state.timeouts:
        request_state.timeouts[msg.request_id].cancel()
        del request_state.timeouts[msg.request_id]
    
    if not msg.success or not msg.candidates:
        # No candidates found - send failure response to user
        final_response = FinalResponse(
            request_id=msg.request_id,
            success=False,
            message="No products found matching your criteria"
        )
        
        await ctx.send(request_data["user_address"], final_response)
        del request_state.requests[msg.request_id]
        return
    
    # Update request state
    request_data["stage"] = "normalization"
    request_data["stages_completed"].append("discovery")
    request_data["candidates"] = [candidate.dict() for candidate in msg.candidates]
    
    # For demo purposes, skip normalization and ranking, go directly to final response
    # In production, you would send to normalizer, then ranker, then verifier
    
    # Convert candidates to final format
    recommendations = []
    for candidate in msg.candidates[:3]:  # Top 3
        recommendation = {
            "name": candidate.name,
            "price": candidate.price or 0.0,
            "rating": candidate.stars or 0.0,
            "overall_score": 7.5,  # Mock score
            "pros": ["Generally positive feedback"],
            "cons": ["Minor issues reported"],
            "summary": f"Found via {candidate.source}",
            "review_count": len(candidate.reviews),
            "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=300&h=300&fit=crop"
        }
        recommendations.append(recommendation)
    
    # Send final response to user
    final_response = FinalResponse(
        request_id=msg.request_id,
        success=True,
        recommendations=recommendations,
        total_found=len(msg.candidates),
        message="Product recommendations found successfully"
    )
    
    await ctx.send(request_data["user_address"], final_response)
    ctx.logger.info(f"Sent final response to user for {msg.request_id}")
    
    # Cleanup request state
    del request_state.requests[msg.request_id]

@planner_protocol.on_message(model=ErrorResponse)
async def handle_error_response(ctx: Context, sender: str, msg: ErrorResponse):
    """Handle error responses from other agents"""
    ctx.logger.error(f"Received error from {sender} for {msg.request_id}: {msg.error}")
    
    if msg.request_id not in request_state.requests:
        return
    
    request_data = request_state.requests[msg.request_id]
    
    # Cancel timeout
    if msg.request_id in request_state.timeouts:
        request_state.timeouts[msg.request_id].cancel()
        del request_state.timeouts[msg.request_id]
    
    # Send error response to user
    final_response = FinalResponse(
        request_id=msg.request_id,
        success=False,
        message=f"Error in {msg.source_agent}: {msg.error}"
    )
    
    await ctx.send(request_data["user_address"], final_response)
    
    # Cleanup
    del request_state.requests[msg.request_id]

async def handle_request_timeout(ctx: Context, request_id: str, stage: str, timeout_seconds: int):
    """Handle request timeouts"""
    try:
        await asyncio.sleep(timeout_seconds)
        
        if request_id in request_state.requests:
            ctx.logger.warning(f"Request {request_id} timed out at stage {stage}")
            
            request_data = request_state.requests[request_id]
            
            # Send timeout response to user
            final_response = FinalResponse(
                request_id=request_id,
                success=False,
                message=f"Request timed out at {stage} stage"
            )
            
            await ctx.send(request_data["user_address"], final_response)
            
            # Cleanup
            del request_state.requests[request_id]
            if request_id in request_state.timeouts:
                del request_state.timeouts[request_id]
                
    except asyncio.CancelledError:
        # Timeout was cancelled (normal case when response received)
        pass

def build_shopping_brief(query: str, constraints: Dict, request_id: str) -> ShoppingBrief:
    """Build shopping brief from user input"""
    
    # Detect category
    category = detect_category(query)
    
    # Extract use case
    use_case = extract_use_case(query)
    
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
        "min_reviews": 5
    }
    
    return ShoppingBrief(
        request_id=request_id,
        query=query,
        category=category,
        use_case=use_case,
        constraints=constraints,
        weights=weights,
        success=success
    )

def detect_category(query: str) -> Optional[str]:
    """Detect product category from query"""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["earbuds", "headphones", "airpods", "wireless"]):
        return "wireless_earbuds"
    elif any(word in query_lower for word in ["desk", "standing", "sit-stand", "workstation"]):
        return "standing_desk"
    elif any(word in query_lower for word in ["laptop", "macbook", "notebook", "computer"]):
        return "laptop"
    
    return None

def extract_use_case(query: str) -> Optional[str]:
    """Extract use case from query"""
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

# Include the protocol in the agent
planner_agent.include(planner_protocol)

if __name__ == "__main__":
    print(f"Starting Planner Agent...")
    print(f"Agent address: {planner_agent.address}")
    planner_agent.run()

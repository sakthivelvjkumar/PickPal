"""
Client Example - How to interact with the uAgent shopping system
Demonstrates how to send requests to the Planner Agent and receive responses
"""

import asyncio
import uuid
from pydantic import BaseModel
from typing import Dict, List

from uagents import Agent, Context, Protocol
from uagents.setup import fund_agent_if_low

# Import message models
from planner_uagent import ShoppingRequest, FinalResponse

# Create a client agent
client_agent = Agent(
    name="shopping_client",
    port=8002,
    seed="client_agent_seed_phrase_unique_789",
    endpoint=["http://localhost:8002/submit"]
)

fund_agent_if_low(client_agent.wallet.address())

# Client protocol
client_protocol = Protocol("ShoppingClient", version="1.0")

# Planner agent address (in production, would be discovered)
PLANNER_ADDRESS = "agent1qw8s7d9k2j3h4g5f6d7s8a9z0x1c2v3b4n5m6"  # Mock address

@client_agent.on_event("startup")
async def setup_client(ctx: Context):
    """Initialize client and send test requests"""
    ctx.logger.info("Shopping Client starting up...")
    ctx.logger.info(f"Client address: {client_agent.address}")
    
    # Wait a bit for other agents to be ready
    await asyncio.sleep(2)
    
    # Send test shopping requests
    await send_test_requests(ctx)

async def send_test_requests(ctx: Context):
    """Send test shopping requests to the planner"""
    
    test_queries = [
        {
            "query": "best wireless earbuds under $150",
            "constraints": {"max_price": 150.0, "min_rating": 4.0}
        },
        {
            "query": "standing desk for home office",
            "constraints": {"max_price": 800.0}
        },
        {
            "query": "gaming laptop under $1200",
            "constraints": {"max_price": 1200.0, "min_rating": 4.2}
        }
    ]
    
    for i, test_case in enumerate(test_queries):
        request_id = f"test_request_{i}_{uuid.uuid4().hex[:8]}"
        
        shopping_request = ShoppingRequest(
            request_id=request_id,
            query=test_case["query"],
            constraints=test_case["constraints"],
            user_address=client_agent.address
        )
        
        ctx.logger.info(f"Sending request {request_id}: {test_case['query']}")
        
        try:
            await ctx.send(PLANNER_ADDRESS, shopping_request)
            ctx.logger.info(f"Successfully sent request {request_id}")
        except Exception as e:
            ctx.logger.error(f"Failed to send request {request_id}: {e}")
        
        # Wait between requests
        await asyncio.sleep(1)

@client_protocol.on_message(model=FinalResponse)
async def handle_shopping_response(ctx: Context, sender: str, msg: FinalResponse):
    """Handle responses from the planner agent"""
    ctx.logger.info(f"Received response for {msg.request_id} from {sender}")
    
    if msg.success:
        ctx.logger.info(f"SUCCESS: {msg.message}")
        ctx.logger.info(f"Found {msg.total_found} products, showing {len(msg.recommendations)} recommendations:")
        
        for i, rec in enumerate(msg.recommendations, 1):
            ctx.logger.info(f"  {i}. {rec['name']}")
            ctx.logger.info(f"     Price: ${rec['price']:.2f}, Rating: {rec['rating']:.1f}★")
            ctx.logger.info(f"     Score: {rec['overall_score']:.1f}/10")
            ctx.logger.info(f"     Pros: {', '.join(rec['pros'][:2])}")
            ctx.logger.info(f"     Cons: {', '.join(rec['cons'][:2])}")
            ctx.logger.info(f"     Summary: {rec['summary']}")
            ctx.logger.info("")
    else:
        ctx.logger.error(f"FAILED: {msg.message}")

# Include protocol
client_agent.include(client_protocol)

if __name__ == "__main__":
    print("Starting Shopping Client...")
    print(f"Client address: {client_agent.address}")
    print("Will send test requests to Planner Agent...")
    client_agent.run()

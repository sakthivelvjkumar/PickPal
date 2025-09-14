from uagents import Agent, Context, Model
import httpx
import asyncio
from typing import Optional, List, Dict, Any
import json

class SearchRequest(Model):
    query: str
    user_id: Optional[str] = None

class SearchResponse(Model):
    status: str
    products: List[Dict[str, Any]]
    processing_time: float
    query_analysis: Dict[str, Any]
    agent_execution: Optional[Dict[str, Any]] = None

# Your unique seed phrase
SEED_PHRASE = "ai_shopping_assistant_demo_seed_phrase_2024"

# Gateway agent that connects FetchAI network to your existing FastAPI system
agent = Agent(
    name="ai_shopping_assistant",
    port=8001,  # Different port from your FastAPI (8000)
    seed=SEED_PHRASE,
    mailbox=True,
    publish_agent_details=True,
    readme_path="README.md"
)

print(f"🤖 FetchAI Shopping Assistant Address: {agent.address}")
print(f"🔗 Make sure your FastAPI server is running on http://localhost:8000")

@agent.on_message(model=SearchRequest)
async def handle_search_request(ctx: Context, sender: str, msg: SearchRequest):
    """Handle search requests from FetchAI network - calls your existing system"""
    ctx.logger.info(f"📝 Received search query from {sender}: {msg.query}")
    
    try:
        # 🎯 This calls your EXISTING FastAPI system
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/search",  # Your existing main.py server
                json={"query": msg.query, "user_id": msg.user_id},
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                
                ctx.logger.info(f"✅ Successfully processed: {len(result.get('products', []))} recommendations")
                
                # Send response back through FetchAI network
                await ctx.send(sender, SearchResponse(
                    status=result["status"],
                    products=result.get("products", []),
                    processing_time=result["processing_time"],
                    query_analysis=result.get("query_analysis", {}),
                    agent_execution=result.get("agent_execution", {})
                ))
                
            else:
                ctx.logger.error(f"❌ FastAPI returned status {response.status_code}")
                await ctx.send(sender, SearchResponse(
                    status="error",
                    products=[],
                    processing_time=0.0,
                    query_analysis={},
                    agent_execution={"error": f"Backend returned {response.status_code}"}
                ))
                
    except httpx.ConnectError:
        ctx.logger.error("🔌 Cannot connect to FastAPI backend - make sure it's running on port 8000")
        await ctx.send(sender, SearchResponse(
            status="error",
            products=[],
            processing_time=0.0,
            query_analysis={},
            agent_execution={"error": "Backend not available"}
        ))
        
    except Exception as e:
        ctx.logger.error(f"💥 Search failed: {str(e)}")
        await ctx.send(sender, SearchResponse(
            status="error", 
            products=[], 
            processing_time=0.0,
            query_analysis={},
            agent_execution={"error": str(e)}
        ))

@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("🚀 AI Shopping Assistant Gateway started!")
    ctx.logger.info("🔗 Ready to bridge FetchAI network to 5-agent shopping system")
    
    # Test connection to your backend
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=5.0)
            if response.status_code == 200:
                ctx.logger.info("✅ Backend connection successful!")
            else:
                ctx.logger.warning("⚠️ Backend health check failed")
    except:
        ctx.logger.error("❌ Cannot connect to backend - make sure FastAPI is running")

@agent.on_interval(period=60.0)  # Every minute
async def health_monitor(ctx: Context):
    """Monitor backend health"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=5.0)
            if response.status_code != 200:
                ctx.logger.warning("⚠️ Backend health check failed")
    except:
        ctx.logger.error("💔 Backend appears to be down")

if __name__ == "__main__":
    print("🎯 Starting FetchAI Gateway for AI Shopping Assistant...")
    print("📋 This agent bridges the FetchAI network to your 5-agent system")
    agent.run()
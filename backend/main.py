import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Dict, Any, List
from pydantic import BaseModel
from services.claude_service import claude_service
class RefineRequest(BaseModel):
    original_query: str
    current_results: List[Dict[str, Any]]
    user_feedback: str

@app.post("/refine")
async def refine_search(request: RefineRequest):
    """Handle conversational refinement using Claude"""
    try:
        refinement = await claude_service.handle_conversational_refinement(
            request.original_query,
            request.current_results,
            request.user_feedback
        )
        if refinement.get('new_search_needed'):
            # Trigger new search with refined query
            new_result = await orchestrator.execute_search(
                refinement.get('suggested_query', request.original_query)
            )
            return {
                "status": "refined",
                "explanation": refinement.get('explanation'),
                "new_results": new_result
            }
        return {
            "status": "understood", 
            "explanation": refinement.get('explanation'),
            "refinement": refinement
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from agents.base_agent import EventBus
from models.schemas import SearchRequest, SearchResponse
from orchestrator import AgentOrchestrator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Shopping Assistant", version="1.0.0", description="5-Agent AI Shopping Assistant for FetchAI Challenge")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent system
event_bus = EventBus()
orchestrator = AgentOrchestrator(event_bus)

@app.on_event("startup")
async def startup_event():
    """Initialize the 5-agent system"""
    logger.info("Initializing AI Shopping Assistant with 5-Agent Architecture...")
    await orchestrator.initialize()
    logger.info("All agents initialized and ready!")

@app.post("/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """Main search endpoint coordinating all 5 agents"""
    start_time = time.time()
    
    try:
        logger.info(f"Processing search query: {request.query}")
        
        # Execute the full 5-agent workflow
        result = await orchestrator.execute_search(request.query, request.user_id)
        
        processing_time = time.time() - start_time
        
        response = SearchResponse(
            status=result['status'],
            products=result.get('recommendations', []),
            processing_time=processing_time,
            query_analysis=result.get('query_analysis', {}),
            agent_execution=result.get('execution_summary', {})
        )
        
        logger.info(f"Search completed in {processing_time:.2f}s with {len(response.products)} recommendations")
        return response
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check showing all agent status"""
    return {
        "status": "healthy", 
        "agents": orchestrator.get_agent_status(),
        "architecture": "5-Agent System (Intent→Discovery→Normalization→Scoring→Verification)"
    }

@app.get("/")
async def root():
    return {
        "message": "AI Shopping Assistant - 5-Agent Architecture",
        "challenge": "FetchAI Bridge Intent and Action",
        "agents": [
            "Intent & Planner Agent",
            "Discovery Agent", 
            "Normalization & Metadata Agent",
            "Scoring & Ranking Agent",
            "Verifier & Adaptation Agent"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
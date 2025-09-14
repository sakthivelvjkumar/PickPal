from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from typing import List, Dict, Any, Optional
import aiosqlite
from datetime import datetime
import sys
import os

# Add src to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.planner.agent import PlannerAgent
from src.common.utils import logger, generate_request_id

app = FastAPI(title="AI Shopping API", description="AI-powered product recommendation system with agent architecture")

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

DATABASE_PATH = "search_history.db"

# Initialize the planner agent
planner = PlannerAgent()

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                results_count INTEGER NOT NULL
            )
        """)
        await db.commit()

@app.on_event("startup")
async def startup_event():
    await init_db()
    logger.info("AI Shopping API started with agent architecture")

class SearchQuery(BaseModel):
    query: str
    max_price: Optional[float] = None
    min_rating: Optional[float] = None

class SearchHistoryItem(BaseModel):
    id: str
    query: str
    timestamp: datetime
    results_count: int

class SearchHistoryCreate(BaseModel):
    query: str
    results_count: int
    max_price: Optional[float] = None
    min_rating: Optional[float] = None

class ProductRecommendation(BaseModel):
    name: str
    price: float
    rating: float
    overall_score: float
    pros: List[str]
    cons: List[str]
    summary: str
    review_count: int
    image_url: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    recommendations: List[ProductRecommendation]
    total_found: int

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/search", response_model=SearchResponse)
async def search_products(query: SearchQuery):
    """Search for products using the new agent-based architecture."""
    try:
        request_id = generate_request_id()
        
        # Build constraints from query parameters
        constraints = {}
        if query.max_price:
            constraints["max_price"] = query.max_price
        if query.min_rating:
            constraints["min_rating"] = query.min_rating
        
        # Use the planner agent to handle the entire pipeline
        result = await planner.handle_user_goal(
            query=query.query,
            constraints=constraints,
            request_id=request_id
        )
        
        if not result["success"]:
            return SearchResponse(
                query=query.query,
                recommendations=[],
                total_found=0
            )
        
        # Convert agent results to API format
        recommendations = []
        for rec in result["recommendations"]:
            recommendation = ProductRecommendation(
                name=rec["name"],
                price=rec["price"],
                rating=rec["rating"],
                overall_score=rec["overall_score"],
                pros=rec["pros"],
                cons=rec["cons"],
                summary=rec["summary"],
                review_count=rec["review_count"],
                image_url=rec.get("image_url")
            )
            recommendations.append(recommendation)
        
        return SearchResponse(
            query=query.query,
            recommendations=recommendations,
            total_found=result["total_found"]
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing search: {str(e)}")

@app.get("/categories")
async def get_categories():
    """Get available product categories."""
    return {"categories": ["wireless_earbuds", "standing_desk", "laptop"]}

@app.get("/search-history", response_model=List[SearchHistoryItem])
async def get_search_history():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, query, timestamp, results_count FROM search_history ORDER BY timestamp DESC LIMIT 20"
        )
        rows = await cursor.fetchall()
        return [
            SearchHistoryItem(
                id=row[0],
                query=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                results_count=row[3]
            )
            for row in rows
        ]

@app.post("/search-history", response_model=SearchHistoryItem)
async def create_search_history(item: SearchHistoryCreate):
    history_item = SearchHistoryItem(
        id=str(int(datetime.now().timestamp() * 1000)),
        query=item.query,
        timestamp=datetime.now(),
        results_count=item.results_count
    )
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO search_history (id, query, timestamp, results_count) VALUES (?, ?, ?, ?)",
            (history_item.id, history_item.query, history_item.timestamp.isoformat(), history_item.results_count)
        )
        await db.commit()
    
    return history_item

@app.delete("/search-history/{history_id}")
async def delete_search_history(history_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM search_history WHERE id = ?", (history_id,))
        await db.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Search history item not found")
    
    return {"message": "Search history item deleted"}

@app.delete("/search-history")
async def clear_search_history():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM search_history")
        await db.commit()
    
    return {"message": "Search history cleared"}

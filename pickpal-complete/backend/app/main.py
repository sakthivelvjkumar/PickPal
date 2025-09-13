from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from textblob import TextBlob
import random
import json
from typing import List, Dict, Any, Optional
import re
import aiosqlite
from datetime import datetime

app = FastAPI(title="AI Shopping API", description="AI-powered product recommendation system")

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

DATABASE_PATH = "search_history.db"

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

MOCK_REVIEWS = {
    "wireless earbuds": [
        {
            "product": "Sony WF-1000XM4",
            "price": 149.99,
            "rating": 4.4,
            "reviews": [
                "Amazing noise cancellation, best I've ever used. Battery life is excellent too.",
                "Sound quality is incredible, very comfortable to wear for hours.",
                "The case is a bit bulky but the earbuds themselves are perfect.",
                "Sometimes connectivity issues with my phone, but overall great product.",
                "Worth every penny, the ANC is game-changing for commuting."
            ],
            "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=300&h=300&fit=crop"
        },
        {
            "product": "Apple AirPods Pro 2",
            "price": 179.99,
            "rating": 4.6,
            "reviews": [
                "Perfect integration with iPhone, seamless switching between devices.",
                "The spatial audio feature is mind-blowing for movies and music.",
                "A bit expensive but the build quality justifies the price.",
                "Battery life could be better, but the quick charge feature helps.",
                "Best earbuds for iOS users, no competition."
            ],
            "image_url": "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=300&h=300&fit=crop"
        },
        {
            "product": "Bose QuietComfort Earbuds",
            "price": 199.99,
            "rating": 4.3,
            "reviews": [
                "Unmatched noise cancellation, perfect for flights and busy environments.",
                "Comfortable fit, stays in ears during workouts.",
                "Sound quality is good but not as crisp as some competitors.",
                "The app could be more intuitive, but the earbuds are solid.",
                "Great for calls, microphone quality is excellent."
            ],
            "image_url": "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=300&h=300&fit=crop"
        }
    ],
    "standing desk": [
        {
            "product": "UPLIFT V2 Standing Desk",
            "price": 599.99,
            "rating": 4.7,
            "reviews": [
                "Extremely sturdy, no wobbling even at full height. Assembly was straightforward.",
                "The motor is quiet and smooth, height adjustment is effortless.",
                "Great build quality, feels like it will last for years.",
                "A bit pricey but worth it for the quality and warranty.",
                "Perfect size for my home office, highly recommend."
            ],
            "image_url": "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=300&h=300&fit=crop"
        },
        {
            "product": "FlexiSpot E7 Standing Desk",
            "price": 399.99,
            "rating": 4.4,
            "reviews": [
                "Good value for money, solid construction and smooth operation.",
                "Easy to assemble, clear instructions and all parts included.",
                "Height range is perfect for most people, very stable.",
                "The desktop could be thicker, but overall satisfied with purchase.",
                "Great customer service when I had questions about setup."
            ],
            "image_url": "https://images.unsplash.com/photo-1541558869434-2840d308329a?w=300&h=300&fit=crop"
        },
        {
            "product": "IKEA Bekant Sit/Stand Desk",
            "price": 249.99,
            "rating": 4.1,
            "reviews": [
                "Budget-friendly option that gets the job done. Not the sturdiest but adequate.",
                "Simple design, fits well in small spaces.",
                "Manual adjustment takes some effort, but it's reliable.",
                "Good starter standing desk, perfect for trying out the concept.",
                "Assembly instructions could be clearer, but manageable."
            ],
            "image_url": "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=300&h=300&fit=crop"
        }
    ],
    "laptop": [
        {
            "product": "MacBook Air M2",
            "price": 1199.99,
            "rating": 4.8,
            "reviews": [
                "Incredible performance and battery life, perfect for productivity and creative work.",
                "The display is gorgeous, colors are vibrant and text is crisp.",
                "Fanless design means completely silent operation, great for libraries.",
                "Limited ports might require dongles, but the performance makes up for it.",
                "Best laptop I've ever owned, highly recommend for Mac users."
            ],
            "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300&h=300&fit=crop"
        },
        {
            "product": "Dell XPS 13",
            "price": 999.99,
            "rating": 4.5,
            "reviews": [
                "Excellent build quality, premium feel with great keyboard and trackpad.",
                "Display is sharp and bright, perfect for both work and entertainment.",
                "Good performance for most tasks, handles multitasking well.",
                "Battery life is decent but not exceptional, gets through a work day.",
                "Great Windows laptop, solid choice for professionals."
            ],
            "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=300&h=300&fit=crop"
        },
        {
            "product": "ThinkPad X1 Carbon",
            "price": 1299.99,
            "rating": 4.6,
            "reviews": [
                "Outstanding keyboard, best typing experience on any laptop.",
                "Durable construction, feels like it can handle daily abuse.",
                "Great for business use, excellent security features.",
                "Display could be brighter, but overall very satisfied.",
                "Perfect for professionals who type a lot, highly recommended."
            ],
            "image_url": "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=300&h=300&fit=crop"
        }
    ]
}

def analyze_sentiment(text: str) -> float:
    """Analyze sentiment of text using TextBlob. Returns score between -1 and 1."""
    blob = TextBlob(text)
    return blob.sentiment.polarity

def extract_pros_cons(reviews: List[str]) -> tuple[List[str], List[str]]:
    """Extract pros and cons from reviews using simple keyword analysis."""
    pros = []
    cons = []
    
    positive_keywords = ['great', 'excellent', 'amazing', 'perfect', 'love', 'best', 'good', 'fantastic', 'outstanding', 'incredible']
    negative_keywords = ['bad', 'terrible', 'awful', 'hate', 'worst', 'poor', 'disappointing', 'issues', 'problems', 'expensive']
    
    for review in reviews:
        sentences = review.split('.')
        for sentence in sentences:
            sentence = sentence.strip().lower()
            if not sentence:
                continue
                
            sentiment_score = analyze_sentiment(sentence)
            
            if sentiment_score > 0.1 and any(keyword in sentence for keyword in positive_keywords):
                clean_sentence = sentence.capitalize()
                if len(clean_sentence) > 10 and len(clean_sentence) < 100:
                    pros.append(clean_sentence)
            
            elif sentiment_score < -0.1 or any(keyword in sentence for keyword in negative_keywords):
                clean_sentence = sentence.capitalize()
                if len(clean_sentence) > 10 and len(clean_sentence) < 100:
                    cons.append(clean_sentence)
    
    pros = list(set(pros))[:3]
    cons = list(set(cons))[:3]
    
    return pros, cons

def calculate_overall_score(rating: float, reviews: List[str]) -> float:
    """Calculate overall score based on rating and sentiment analysis."""
    rating_score = (rating / 5.0) * 10
    
    sentiment_scores = [analyze_sentiment(review) for review in reviews]
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    
    sentiment_score = (avg_sentiment + 1) * 5
    
    overall_score = (rating_score * 0.7) + (sentiment_score * 0.3)
    
    return round(overall_score, 1)

def find_matching_products(query: str) -> List[Dict[str, Any]]:
    """Find products matching the search query."""
    query_lower = query.lower()
    matching_products = []
    
    for category, products in MOCK_REVIEWS.items():
        if any(word in query_lower for word in category.split()):
            matching_products.extend(products)
    
    if not matching_products:
        for category, products in MOCK_REVIEWS.items():
            for product in products:
                if any(word in product["product"].lower() for word in query_lower.split()):
                    matching_products.append(product)
    
    return matching_products

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/search", response_model=SearchResponse)
async def search_products(query: SearchQuery):
    """Search for products and return AI-powered recommendations."""
    try:
        matching_products = find_matching_products(query.query)
        
        if not matching_products:
            return SearchResponse(
                query=query.query,
                recommendations=[],
                total_found=0
            )
        
        recommendations = []
        
        for product_data in matching_products:
            if query.max_price and product_data["price"] > query.max_price:
                continue
            if query.min_rating and product_data["rating"] < query.min_rating:
                continue
            
            pros, cons = extract_pros_cons(product_data["reviews"])
            overall_score = calculate_overall_score(product_data["rating"], product_data["reviews"])
            
            summary = f"Highly rated {product_data['product']} with {len(product_data['reviews'])} reviews analyzed."
            
            recommendation = ProductRecommendation(
                name=product_data["product"],
                price=product_data["price"],
                rating=product_data["rating"],
                overall_score=overall_score,
                pros=pros if pros else ["High quality product", "Good value for money"],
                cons=cons if cons else ["No significant issues found"],
                summary=summary,
                review_count=len(product_data["reviews"]),
                image_url=product_data.get("image_url")
            )
            
            recommendations.append(recommendation)
        
        recommendations.sort(key=lambda x: x.overall_score, reverse=True)
        top_recommendations = recommendations[:3]
        
        return SearchResponse(
            query=query.query,
            recommendations=top_recommendations,
            total_found=len(matching_products)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing search: {str(e)}")

@app.get("/categories")
async def get_categories():
    """Get available product categories."""
    return {"categories": list(MOCK_REVIEWS.keys())}

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

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

@dataclass
class ShoppingBrief:
    query: str
    category: str
    budget_max: Optional[float] = None
    budget_min: Optional[float] = None
    priorities: List[str] = field(default_factory=list)
    use_case: Optional[str] = None
    brand_preferences: List[str] = field(default_factory=list)
    excluded_brands: List[str] = field(default_factory=list)
    user_profile: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Product:
    product_id: str
    name: str
    brand: str
    price: float
    rating: float
    review_count: int
    url: str
    image_url: Optional[str] = None
    sku: Optional[str] = None
    asin: Optional[str] = None
    in_stock: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Review:
    review_id: str
    product_id: str
    rating: int
    text: str
    date: datetime
    title: Optional[str] = None
    author: Optional[str] = None
    helpful_votes: int = 0
    verified_purchase: bool = False
    source: str = "unknown"  # "amazon", "reddit", "blog"

@dataclass
class AspectScore:
    aspect: str  # "battery_life", "comfort", "sound_quality"
    score: float  # 0-100
    confidence: float  # 0-1
    supporting_reviews: List[str]
    sentiment_breakdown: Dict[str, int]

@dataclass
class ProductScore:
    product: Product
    overall_score: float  # 0-100
    aspect_scores: List[AspectScore]
    pros: List[str]  # 2-3 items
    cons: List[str]  # 2-3 items
    justification: str  # Why this ranking
    confidence: float

# API Models
class SearchRequest(BaseModel):
    query: str
    user_id: Optional[str] = None

class SearchResponse(BaseModel):
    status: str
    products: List[Dict[str, Any]]
    processing_time: float
    query_analysis: Dict[str, Any]
    agent_execution: Optional[Dict[str, Any]] = None

class ProductResponse(BaseModel):
    name: str
    brand: str
    price: float
    rating: float
    review_count: int
    url: str
    image_url: Optional[str] = None
    overall_score: float
    pros: List[str]
    cons: List[str]
    justification: str

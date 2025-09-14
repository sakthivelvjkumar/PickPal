from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import time

class Trace(BaseModel):
    request_id: str
    step: str
    source_agent: str
    ts: float = Field(default_factory=time.time)

class ShoppingBrief(BaseModel):
    trace: Trace
    query: str
    category: Optional[str] = None
    use_case: Optional[str] = None
    constraints: Dict[str, float | int | str | bool] = {}
    weights: Dict[str, float] = {}
    success: Dict[str, int | bool] = {"k": 3, "diversity": True, "min_reviews": 50}

class ProductCandidate(BaseModel):
    trace: Trace
    name: str
    price: Optional[float] = None
    stars: Optional[float] = None
    category: Optional[str] = None
    urls: Dict[str, str] = {}
    raw_reviews: List[Dict] = []  # {text, stars, date, helpful, verified}
    meta: Dict[str, float | int | str | List[str]] = {}

class EnrichedProduct(BaseModel):
    trace: Trace
    canonical_id: str
    name: str
    price: Optional[float] = None
    stars: Optional[float] = None
    reviews_total: Optional[int] = None
    signals: Dict[str, float] = {}  # verified_pct, avg_helpful, recency_days_p50
    aspect_frequencies: Dict[str, float] = {}  # aspect frequency (for weighting)
    raw_reviews: List[Dict] = []  # Keep original reviews for pros/cons extraction

class RankedProduct(BaseModel):
    trace: Trace
    canonical_id: str
    name: str
    score: float
    pros: List[str]
    cons: List[str]
    why: Dict[str, float]  # rating/sentiment/recency/helpfulness weights
    price: Optional[float] = None
    stars: Optional[float] = None

class RankedList(BaseModel):
    trace: Trace
    items: List[RankedProduct]

class ClarificationRequest(BaseModel):
    trace: Trace
    missing: List[str]
    suggested_questions: List[str]
    context: Dict[str, str]

class ClarificationAnswer(BaseModel):
    trace: Trace
    answers: Dict[str, str | float | int | Dict[str, float]]

class VerificationReport(BaseModel):
    trace: Trace
    passed: bool
    checks: Dict[str, bool]
    notes: List[str] = []

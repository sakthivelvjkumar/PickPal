from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from dataclasses import dataclass, field
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

@dataclass
class ProductCandidate:
    """A product candidate discovered from various sources."""
    name: str
    price: Optional[float] = None
    stars: Optional[float] = None
    url: Optional[str] = None
    raw_reviews: List[Dict] = field(default_factory=list)
    meta: Dict = field(default_factory=dict)  # Source-specific metadata
    trace: Optional[Trace] = None
    image_url: Optional[str] = None

@dataclass
class EnrichedProduct:
    """A product with enriched data and quality signals."""
    name: str
    price: float
    stars: float
    url: str
    raw_reviews: List[Dict]
    aspects: Dict[str, float]  # Aspect scores (e.g., {"sound_quality": 4.2, "battery": 3.8})
    quality_signals: Dict[str, float]  # Quality indicators
    meta: Dict = field(default_factory=dict)
    trace: Optional['Trace'] = None
    image_url: Optional[str] = None

@dataclass
class RankedProduct:
    """A product with ranking score and extracted insights."""
    name: str
    price: float
    stars: float
    url: str
    raw_reviews: List[Dict]
    aspects: Dict[str, float]
    quality_signals: Dict[str, float]
    score: float  # Composite ranking score
    pros: List[str]  # Extracted pros
    cons: List[str]  # Extracted cons
    why: Dict[str, float]  # Explanation of ranking
    meta: Dict = field(default_factory=dict)
    trace: Optional['Trace'] = None
    image_url: Optional[str] = None

@dataclass
class RankedList:
    trace: 'Trace'
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

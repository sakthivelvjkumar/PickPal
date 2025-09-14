from pydantic_settings import BaseSettings
from typing import Dict, Any

class Settings(BaseSettings):
    # Agent Configuration
    AGENT_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    
    # Scoring Weights
    SCORING_WEIGHTS: Dict[str, float] = {
        "rating": 0.25,
        "sentiment": 0.30,
        "recency": 0.15,
        "helpfulness": 0.15,
        "verified": 0.15
    }
    
    # Search Configuration
    MAX_PRODUCTS: int = 15
    MIN_PRODUCTS: int = 3
    REVIEWS_PER_PRODUCT: int = 10
    
    # Response Configuration
    RESPONSE_TIMEOUT: float = 3.0
    TOP_RECOMMENDATIONS: int = 3
    
    class Config:
        env_file = ".env"

settings = Settings()

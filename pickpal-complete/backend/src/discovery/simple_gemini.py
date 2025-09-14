import json
import re
from typing import List, Dict, Optional
import google.generativeai as genai
from datetime import datetime
from ..common.utils import logger, log_context

class SimpleGeminiSearch:
    """Simple Gemini search for direct product recommendations without agent pipeline."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of Gemini model."""
        if not self._initialized:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self._initialized = True
    
    async def search_simple(self, query: str, max_price: Optional[float] = None, min_rating: Optional[float] = None) -> List[Dict]:
        """Generate simple product recommendations using Gemini API."""
        try:
            self._ensure_initialized()
            
            prompt = self._build_simple_prompt(query, max_price, min_rating)
            response = self.model.generate_content(prompt)
            products = self._parse_simple_response(response.text)
            
            return products[:3]  # Always return exactly 3 products
            
        except Exception as e:
            logger.error(f"Simple Gemini search error: {e}")
            return self._generate_simple_fallback(query)
    
    def _build_simple_prompt(self, query: str, max_price: Optional[float], min_rating: Optional[float]) -> str:
        """Build a simple prompt for direct product recommendations."""
        constraints = []
        if max_price:
            constraints.append(f"under ${max_price}")
        if min_rating:
            constraints.append(f"rating above {min_rating} stars")
        
        constraint_text = " with " + " and ".join(constraints) if constraints else ""
        
        return f"""You are a product recommendation expert. Generate exactly 3 realistic product recommendations for: "{query}"{constraint_text}

CRITICAL: You must respond with ONLY a valid JSON array. No explanations, no markdown, no extra text.

For each product, use this exact structure:
{{
  "name": "Specific Brand Model Name",
  "price": 99.99,
  "rating": 4.5,
  "overall_score": 8.2,
  "pros": ["Specific feature 1", "Specific feature 2", "Specific feature 3"],
  "cons": ["Specific limitation 1", "Specific limitation 2"],
  "summary": "One sentence explaining why this product stands out for the query",
  "review_count": 247,
  "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=300&h=300&fit=crop"
}}

REQUIREMENTS:
- Use real brand names and realistic model names
- Prices must respect the constraint: {f"under ${max_price}" if max_price else "varied price points"}
- Ratings must be realistic (3.5-4.8 range)
- Overall scores: 6.5-9.2 range, correlate with price/quality
- Pros/cons must be specific to the product category, not generic
- Review counts: 80-450 range
- Use appropriate Unsplash photo IDs for the product category

EXAMPLES OF GOOD RESPONSES:
For "water bottles": Hydro Flask, Nalgene, Simple Modern
For "headphones": Sony WH-1000XM4, Bose QuietComfort, Audio-Technica ATH-M50x
For "laptops": MacBook Air M2, Dell XPS 13, ThinkPad X1 Carbon

Return format: [product1, product2, product3]
"""
    
    def _parse_simple_response(self, response_text: str) -> List[Dict]:
        """Parse Gemini response into simple product format."""
        try:
            cleaned_text = self._extract_json_from_response(response_text)
            products_data = json.loads(cleaned_text)
            
            if not isinstance(products_data, list):
                products_data = [products_data]
            
            # Ensure all required fields are present
            for product in products_data:
                product.setdefault("name", "Unknown Product")
                product.setdefault("price", 99.99)
                product.setdefault("rating", 4.0)
                product.setdefault("overall_score", 7.0)
                product.setdefault("pros", ["Good quality", "Reliable", "Good value"])
                product.setdefault("cons", ["Could be improved", "Minor issues"])
                product.setdefault("summary", "Recommended product with good features")
                product.setdefault("review_count", 150)
                product.setdefault("image_url", "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=300&h=300&fit=crop")
                product.setdefault("sample_reviews", ["Good product", "Decent quality"])
            
            return products_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse simple Gemini JSON: {e}")
            return self._generate_simple_fallback("product search")
        except Exception as e:
            logger.error(f"Error parsing simple Gemini response: {e}")
            return self._generate_simple_fallback("product search")
    
    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON from Gemini response text."""
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        json_match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        return text.strip()
    
    def _generate_simple_fallback(self, query: str) -> List[Dict]:
        """Generate simple fallback products."""
        return [
            {
                "name": f"AI-Generated Product for '{query}' #1",
                "price": 99.99,
                "rating": 4.2,
                "overall_score": 8.1,
                "pros": ["Good quality", "Reliable performance", "Good value for money"],
                "cons": ["Could be improved", "Minor design issues"],
                "summary": "Solid choice with good features and reliable performance",
                "review_count": 156,
                "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=300&h=300&fit=crop",
                "sample_reviews": ["Great product, meets expectations", "Good quality for the price"]
            },
            {
                "name": f"AI-Generated Product for '{query}' #2",
                "price": 149.99,
                "rating": 4.5,
                "overall_score": 8.5,
                "pros": ["Excellent features", "Premium quality", "Great design"],
                "cons": ["Higher price point", "Limited availability"],
                "summary": "Premium option with excellent features and build quality",
                "review_count": 203,
                "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=300&h=300&fit=crop",
                "sample_reviews": ["Outstanding quality, worth the price", "Excellent features and performance"]
            },
            {
                "name": f"AI-Generated Product for '{query}' #3",
                "price": 79.99,
                "rating": 4.0,
                "overall_score": 7.8,
                "pros": ["Budget-friendly", "Decent performance", "Good starter option"],
                "cons": ["Basic features", "Build quality could be better"],
                "summary": "Budget-friendly option with decent performance for the price",
                "review_count": 89,
                "image_url": "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=300&h=300&fit=crop",
                "sample_reviews": ["Good for the price", "Decent quality, basic features"]
            }
        ]

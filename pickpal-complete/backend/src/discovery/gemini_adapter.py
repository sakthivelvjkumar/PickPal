import json
import re
from typing import List, Dict, Optional
import google.generativeai as genai
from datetime import datetime
from ..common.utils import logger, log_context

class GeminiAdapter:
    """Adapter for Gemini API to generate product recommendations."""
    
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
    
    async def search_products(self, queries: List[str], category: str, max_results: int = 3) -> List[Dict]:
        """Generate product recommendations using Gemini API."""
        try:
            # Ensure model is initialized
            self._ensure_initialized()
            
            # Use the first query as the main search term
            main_query = queries[0] if queries else "product recommendations"
            
            prompt = self._build_product_prompt(main_query, category, max_results)
            
            response = self.model.generate_content(prompt)
            products = self._parse_gemini_response(response.text)
            
            return products[:max_results]
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return []
    
    def _build_product_prompt(self, query: str, category: str, max_results: int) -> str:
        """Build a structured prompt for Gemini to generate product recommendations."""
        return f"""
You are a product recommendation expert. Generate exactly {max_results} realistic product recommendations for: "{query}"

For each product, provide the following information in this exact JSON format:
{{
  "name": "Product Name",
  "price": 99.99,
  "stars": 4.5,
  "url": "https://example.com/product",
  "reviews": [
    {{
      "text": "Great product, excellent quality and value",
      "stars": 5,
      "verified": true,
      "helpful": 15,
      "date": "2024-01-15"
    }},
    {{
      "text": "Good overall but could be improved",
      "stars": 4,
      "verified": true,
      "helpful": 8,
      "date": "2024-01-10"
    }}
  ],
  "reviews_count": 247,
  "source": "gemini_ai",
  "last_updated": "2024-01-20T10:00:00",
  "evidence_score": 4,
  "evidence_notes": ["High review count", "Recent reviews", "Verified purchases"]
}}

Requirements:
- Products should be realistic and currently available
- Include varied price points
- Generate 2-3 realistic reviews per product
- Use current dates (2024)
- Make reviews specific to the product category
- Include both positive and constructive feedback
- Ensure star ratings are realistic (3.5-5.0 range)

Return ONLY a JSON array of {max_results} products, no additional text.
"""
    
    def _parse_gemini_response(self, response_text: str) -> List[Dict]:
        """Parse Gemini response into product candidate format."""
        try:
            # Clean the response to extract JSON
            cleaned_text = self._extract_json_from_response(response_text)
            
            # Parse JSON
            products_data = json.loads(cleaned_text)
            
            # Ensure it's a list
            if not isinstance(products_data, list):
                products_data = [products_data]
            
            # Convert to our format
            products = []
            for product in products_data:
                candidate = {
                    "name": product.get("name", "Unknown Product"),
                    "price": float(product.get("price", 0.0)),
                    "stars": float(product.get("stars", 4.0)),
                    "url": product.get("url", "https://example.com"),
                    "reviews": product.get("reviews", []),
                    "reviews_count": product.get("reviews_count", len(product.get("reviews", []))),
                    "source": "gemini_ai",
                    "last_updated": datetime.now().isoformat(),
                    "evidence_score": product.get("evidence_score", 3),
                    "evidence_notes": product.get("evidence_notes", ["AI-generated recommendation"])
                }
                products.append(candidate)
            
            return products
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            return self._generate_fallback_products()
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return self._generate_fallback_products()
    
    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON from Gemini response text."""
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find JSON array or object
        json_match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        return text.strip()
    
    def _generate_fallback_products(self) -> List[Dict]:
        """Generate fallback products if Gemini parsing fails."""
        return [
            {
                "name": "AI-Generated Product 1",
                "price": 99.99,
                "stars": 4.2,
                "url": "https://example.com/product1",
                "reviews": [
                    {
                        "text": "Good quality product, meets expectations",
                        "stars": 4,
                        "verified": True,
                        "helpful": 10,
                        "date": "2024-01-15"
                    }
                ],
                "reviews_count": 150,
                "source": "gemini_ai",
                "last_updated": datetime.now().isoformat(),
                "evidence_score": 3,
                "evidence_notes": ["AI-generated fallback"]
            },
            {
                "name": "AI-Generated Product 2",
                "price": 149.99,
                "stars": 4.5,
                "url": "https://example.com/product2",
                "reviews": [
                    {
                        "text": "Excellent value for money, highly recommended",
                        "stars": 5,
                        "verified": True,
                        "helpful": 18,
                        "date": "2024-01-12"
                    }
                ],
                "reviews_count": 203,
                "source": "gemini_ai",
                "last_updated": datetime.now().isoformat(),
                "evidence_score": 4,
                "evidence_notes": ["AI-generated fallback"]
            },
            {
                "name": "AI-Generated Product 3",
                "price": 79.99,
                "stars": 4.0,
                "url": "https://example.com/product3",
                "reviews": [
                    {
                        "text": "Decent product, some room for improvement",
                        "stars": 4,
                        "verified": True,
                        "helpful": 7,
                        "date": "2024-01-10"
                    }
                ],
                "reviews_count": 89,
                "source": "gemini_ai",
                "last_updated": datetime.now().isoformat(),
                "evidence_score": 3,
                "evidence_notes": ["AI-generated fallback"]
            }
        ]

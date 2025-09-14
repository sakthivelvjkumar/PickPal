import asyncio
import json
from typing import Dict, Any, List, Optional
from anthropic import AsyncAnthropic
from config import settings
import logging

logger = logging.getLogger(__name__)

class ClaudeService:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
    
    async def analyze_shopping_intent(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Advanced intent analysis with Claude's sophisticated understanding"""
        
        prompt = f"""You are an expert shopping consultant with deep understanding of consumer needs. 
        Analyze this shopping query and extract detailed requirements:

        Query: \"{query}\"
        User Context: {json.dumps(user_context or {}, indent=2)}

        Extract and return a JSON object with:
        1. product_category: specific category (earbuds, headphones, gaming_headset, etc.)
        2. budget_constraints: {{min: number, max: number, currency: \"USD\"}}
        3. use_case_analysis: {{
            primary_use: string,
            usage_environment: string,
            usage_duration: string,
            user_type: string (casual, professional, enthusiast, etc.)
        }}
        4. explicit_priorities: [list of stated requirements]
        5. implicit_priorities: [list of inferred needs based on use case]
        6. deal_breakers: [list of things to avoid]
        7. brand_preferences: {{preferred: [list], excluded: [list]}}
        8. technical_requirements: [specific features needed]
        9. emotional_drivers: [what user really cares about]
        10. confidence_score: number 0-1 for how well you understand the request

        Be extremely thorough in understanding nuanced requirements, implicit needs, and context clues.
        """

        try:
            response = await self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=settings.CLAUDE_MAX_TOKENS,
                temperature=settings.CLAUDE_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse Claude's JSON response
            result = json.loads(response.content[0].text)
            logger.info(f"Claude intent analysis confidence: {result.get('confidence_score', 0)}")
            return result
            
        except Exception as e:
            logger.error(f"Claude intent analysis failed: {str(e)}")
            return self._fallback_intent_analysis(query)
    
    async def analyze_product_reviews(self, product_name: str, reviews: List[Dict[str, Any]], 
                                    focus_aspects: List[str]) -> Dict[str, Any]:
        """Deep review analysis using Claude's contextual understanding"""
        
        # Limit reviews to avoid token limits
        review_texts = []
        for review in reviews[:15]:  # Top 15 reviews
            review_texts.append(f"Rating: {review.get('rating')}/5 - {review.get('text', '')}")
        
        reviews_text = "\n\n".join(review_texts)
        aspects_text = ", ".join(focus_aspects)
        
        prompt = f"""You are an expert product analyst. Analyze these reviews for {product_name} focusing on: {aspects_text}

        Reviews:
        {reviews_text}

        Provide detailed analysis as JSON:
        {{
            "overall_sentiment": {{"score": 0-100, "confidence": 0-1, "reasoning": "explanation"}},
            "aspect_analysis": {{
                "{focus_aspects[0] if focus_aspects else 'general'}": {{
                    "score": 0-100,
                    "confidence": 0-1,
                    "positive_mentions": [list of specific positive quotes],
                    "negative_mentions": [list of specific negative quotes],
                    "key_insights": [list of important patterns],
                    "user_type_breakdown": {{"enthusiasts": "sentiment", "casual_users": "sentiment", "professionals": "sentiment"}}
                }}
                // ... for each aspect
            }},
            "pros": [3-4 specific, evidence-based pros with supporting quotes],
            "cons": [2-3 specific, evidence-based cons with supporting quotes],
            "best_for": [types of users who would love this product],
            "not_ideal_for": [types of users who should avoid this],
            "standout_features": [unique selling points mentioned by users],
            "common_complaints": [recurring issues across reviews],
            "quality_indicators": {{
                "review_authenticity": 0-1,
                "review_depth": 0-1,
                "reviewer_expertise": 0-1
            }}
        }}

        Focus on nuanced insights, contradictions, and patterns that basic sentiment analysis would miss.
        """

        try:
            response = await self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=1500,  # More tokens for detailed analysis
                temperature=0.1,  # Lower temperature for analytical tasks
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            logger.info(f"Claude analyzed {len(reviews)} reviews for {product_name}")
            return result
            
        except Exception as e:
            logger.error(f"Claude review analysis failed: {str(e)}")
            return self._fallback_review_analysis(reviews, focus_aspects)
    
    async def generate_personalized_explanation(self, product_score: Dict[str, Any], 
                                               user_query: str, ranking_position: int) -> str:
        """Generate human-like, personalized explanations for rankings"""
        
        prompt = f"""You are a knowledgeable shopping advisor explaining why you ranked this product #{ranking_position} for a customer.

        Original Query: \"{user_query}\"
        Product: {product_score.get('name')} by {product_score.get('brand')}
        Price: ${product_score.get('price')}
        Overall Score: {product_score.get('overall_score')}/100
        Key Pros: {product_score.get('pros', [])}
        Key Cons: {product_score.get('cons', [])}

        Write a conversational, personalized explanation (2-3 sentences) that:
        1. Directly addresses why this fits their specific needs from the query
        2. Acknowledges trade-offs honestly
        3. Uses natural, consultant-like language
        4. References specific aspects they care about
        5. Feels like advice from a trusted friend

        Avoid generic language. Be specific and contextual to their query and this product's strengths.
        """

        try:
            response = await self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=200,
                temperature=0.4,  # Slightly higher for natural language
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Claude explanation generation failed: {str(e)}")
            return f"Ranked #{ranking_position} due to strong performance in key areas important to your query."

    async def handle_conversational_refinement(self, original_query: str, 
                                             current_results: List[Dict[str, Any]], 
                                             user_feedback: str) -> Dict[str, Any]:
        """Handle conversational refinement of search results"""
        
        products_summary = []
        for i, product in enumerate(current_results[:3]):
            products_summary.append(f"#{i+1}: {product.get('name')} - ${product.get('price')} - Score: {product.get('overall_score')}")
        
        prompt = f"""You are a shopping consultant helping a customer refine their search.

        Original Query: \"{original_query}\"
        Current Top Recommendations:
        {chr(10).join(products_summary)}

        Customer Feedback: \"{user_feedback}\"

        Analyze the feedback and provide JSON response:
        {{
            "feedback_type": "refinement|complaint|question|clarification",
            "new_priorities": [list of new/changed priorities],
            "constraints_to_add": [new constraints like budget, brand, features],
            "constraints_to_remove": [constraints to relax],
            "rerank_needed": boolean,
            "new_search_needed": boolean,
            "suggested_query": "refined query string",
            "explanation": "friendly explanation of what you understood and what you'll do"
        }}

        Examples:
        - "Actually, I prefer Sony over Bose" → add brand preference
        - "Too expensive" → lower budget constraint
        - "Battery life is most important" → boost battery life priority
        - "These are all too big" → add size/form factor constraint
        """

        try:
            response = await self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=400,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return json.loads(response.content[0].text)
            
        except Exception as e:
            logger.error(f"Claude conversational refinement failed: {str(e)}")
            return {"feedback_type": "error", "rerank_needed": False}

    def _fallback_intent_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback when Claude API fails"""
        return {
            "product_category": "general",
            "budget_constraints": {"max": None, "min": None},
            "explicit_priorities": [],
            "confidence_score": 0.3
        }
    
    def _fallback_review_analysis(self, reviews: List[Dict], aspects: List[str]) -> Dict[str, Any]:
        """Fallback when Claude API fails"""
        return {
            "overall_sentiment": {"score": 70, "confidence": 0.3},
            "pros": ["Good overall rating from users"],
            "cons": ["Limited analysis available"],
            "aspect_analysis": {}
        }

# Global Claude service instance
claude_service = ClaudeService()

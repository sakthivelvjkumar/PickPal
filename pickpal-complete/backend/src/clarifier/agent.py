from typing import List, Dict
from ..common.messages import *
from ..common.bus import AgentBase
from ..common.utils import logger, log_context

class ClarifierAgent(AgentBase):
    """Agent responsible for asking clarifying questions when needed."""
    
    def __init__(self):
        super().__init__("clarifier")
    
    async def should_clarify(self, brief: ShoppingBrief) -> bool:
        """Determine if clarification is needed based on VOI (Value of Information)."""
        # Simple VOI heuristic - ask for clarification if key info is missing
        
        missing_slots = []
        
        # Check for missing budget constraint
        if "max_price" not in brief.constraints and "budget" not in brief.constraints:
            missing_slots.append("budget")
        
        # Check for missing use case
        if not brief.use_case and not self._has_use_case_in_query(brief.query):
            missing_slots.append("use_case")
        
        # Check for missing priorities/weights
        if not brief.weights:
            missing_slots.append("priorities")
        
        # VOI threshold - ask if we have 2+ missing critical slots
        return len(missing_slots) >= 2
    
    def _has_use_case_in_query(self, query: str) -> bool:
        """Check if query contains use case information."""
        use_case_keywords = [
            "for work", "for gaming", "for running", "for gym", "for travel",
            "for office", "for home", "for commuting", "for calls", "for music"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in use_case_keywords)
    
    async def generate_clarification_request(self, brief: ShoppingBrief) -> ClarificationRequest:
        """Generate clarification questions based on missing information."""
        trace = self.create_trace(brief.trace.request_id, "clarify")
        
        missing = []
        questions = []
        context = {"category": brief.category or ""}
        
        # Budget clarification
        if "max_price" not in brief.constraints:
            missing.append("budget")
            questions.append("What's your budget range for this purchase?")
        
        # Use case clarification
        if not brief.use_case and not self._has_use_case_in_query(brief.query):
            missing.append("use_case")
            if "earbuds" in brief.query.lower() or "headphones" in brief.query.lower():
                questions.append("What will you primarily use these for? (e.g., work calls, music, exercise)")
            elif "desk" in brief.query.lower():
                questions.append("What's your primary use case? (e.g., work from home, gaming, general office)")
            else:
                questions.append("What's your primary use case for this product?")
        
        # Priority clarification
        if not brief.weights:
            missing.append("priorities")
            if "earbuds" in brief.query.lower():
                questions.append("What's most important to you: sound quality, battery life, or comfort?")
            elif "desk" in brief.query.lower():
                questions.append("What's most important: stability, price, or features?")
            else:
                questions.append("What features are most important to you?")
        
        # Limit to 2 questions max
        questions = questions[:2]
        missing = missing[:2]
        
        with log_context(trace.request_id):
            logger.info(f"Generated {len(questions)} clarification questions")
        
        return ClarificationRequest(
            trace=trace,
            missing=missing,
            suggested_questions=questions,
            context=context
        )
    
    def apply_clarification_answers(self, brief: ShoppingBrief, answers: ClarificationAnswer) -> ShoppingBrief:
        """Apply clarification answers to update the shopping brief."""
        updated_constraints = brief.constraints.copy()
        updated_weights = brief.weights.copy()
        updated_use_case = brief.use_case
        
        for key, value in answers.answers.items():
            if key == "budget" or key == "max_price":
                if isinstance(value, (int, float)):
                    updated_constraints["max_price"] = float(value)
                elif isinstance(value, str):
                    # Try to extract number from string like "$150" or "under 200"
                    import re
                    numbers = re.findall(r'\d+', value)
                    if numbers:
                        updated_constraints["max_price"] = float(numbers[0])
            
            elif key == "use_case":
                updated_use_case = str(value)
            
            elif key == "priorities":
                if isinstance(value, dict):
                    updated_weights.update(value)
                elif isinstance(value, str):
                    # Parse priority string
                    priority_weights = self._parse_priority_string(str(value))
                    updated_weights.update(priority_weights)
        
        # Create updated brief
        updated_brief = ShoppingBrief(
            trace=brief.trace,
            query=brief.query,
            category=brief.category,
            use_case=updated_use_case,
            constraints=updated_constraints,
            weights=updated_weights,
            success=brief.success
        )
        
        return updated_brief
    
    def _parse_priority_string(self, priority_str: str) -> Dict[str, float]:
        """Parse priority string into weights."""
        weights = {}
        priority_lower = priority_str.lower()
        
        # Default weights based on mentioned priorities
        if "sound" in priority_lower or "audio" in priority_lower:
            weights["rating"] = 0.5
            weights["sentiment"] = 0.3
        elif "battery" in priority_lower:
            weights["recency"] = 0.4
            weights["rating"] = 0.4
        elif "comfort" in priority_lower:
            weights["sentiment"] = 0.5
            weights["rating"] = 0.3
        elif "price" in priority_lower or "budget" in priority_lower:
            weights["rating"] = 0.6
            weights["helpfulness"] = 0.2
        elif "stability" in priority_lower:
            weights["rating"] = 0.5
            weights["sentiment"] = 0.4
        else:
            # Default balanced weights
            weights = {"rating": 0.4, "sentiment": 0.3, "recency": 0.2, "helpfulness": 0.1}
        
        return weights
    
    async def handle_clarification_request(self, message):
        """Handle clarification request from message bus."""
        try:
            brief = message.payload["data"]
            response_topic = message.payload["response_topic"]
            
            if await self.should_clarify(brief):
                clarification = await self.generate_clarification_request(brief)
                await self.send_message(response_topic, clarification, message.trace)
            else:
                # No clarification needed
                await self.send_message(response_topic, None, message.trace)
            
        except Exception as e:
            with log_context(message.trace.request_id):
                logger.error(f"Clarification request failed: {e}")
            raise

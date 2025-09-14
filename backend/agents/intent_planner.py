import re
import asyncio
from typing import Dict, Any, List, Optional
from textblob import TextBlob
from .base_agent import BaseAgent, EventType
from models.schemas import ShoppingBrief
from services.claude_service import claude_service

class IntentPlannerAgent(BaseAgent):
    def __init__(self, event_bus):
        super().__init__("intent_planner", event_bus)
        self.user_preferences = {}  # Simple in-memory store
        
        # NLP patterns for intent extraction
        self.budget_patterns = [
            r'under \$?(\d+)',
            r'below \$?(\d+)',
            r'less than \$?(\d+)',
            r'budget of \$?(\d+)',
            r'\$(\d+) or less'
        ]
        
        self.category_mapping = {
            'earbuds': ['earbuds', 'ear buds', 'wireless earbuds', 'bluetooth earbuds'],
            'headphones': ['headphones', 'over ear', 'on ear', 'noise cancelling'],
            'gaming': ['gaming headset', 'gaming headphones', 'gaming'],
            'workout': ['workout', 'running', 'sports', 'fitness', 'gym']
        }
        
        self.priority_keywords = {
            'comfort': ['comfort', 'comfortable', 'ergonomic', 'fit'],
            'battery': ['battery', 'battery life', 'playtime', 'listening time'],
            'sound_quality': ['sound', 'audio', 'quality', 'bass', 'treble'],
            'noise_cancellation': ['noise cancelling', 'anc', 'noise reduction'],
            'durability': ['durable', 'build quality', 'sturdy', 'reliable'],
            'price': ['cheap', 'affordable', 'budget', 'value']
        }

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        query = task.get('query', '')
        user_id = task.get('user_id')
        
        await self.emit_event(EventType.TASK_STARTED, {
            'task': 'intent_analysis',
            'query': query
        })
        
        try:
            # Parse the query
            shopping_brief = await self._parse_query(query, user_id)
            
            # Create execution plan
            plan = await self._create_execution_plan(shopping_brief)
            
            result = {
                'shopping_brief': shopping_brief,
                'execution_plan': plan,
                'status': 'success'
            }
            
            await self.emit_event(EventType.TASK_COMPLETED, {
                'task': 'intent_analysis',
                'brief': shopping_brief.__dict__,
                'plan_tasks': len(plan['tasks'])
            })
            
            return result
            
        except Exception as e:
            await self.emit_event(EventType.TASK_FAILED, {
                'task': 'intent_analysis',
                'error': str(e)
            })
            raise

    async def _parse_query(self, query: str, user_id: Optional[str] = None) -> ShoppingBrief:
        """Parse natural language query using Claude's superior understanding"""
        # Get user context if available
        user_context = self.user_preferences.get(user_id, {})
        try:
            # Use Claude for sophisticated intent analysis
            claude_analysis = await claude_service.analyze_shopping_intent(query, user_context)
            # Extract information from Claude's analysis
            category = claude_analysis.get('product_category', 'general')
            budget_constraints = claude_analysis.get('budget_constraints', {})
            budget_max = budget_constraints.get('max')
            # Combine explicit and implicit priorities
            explicit_priorities = claude_analysis.get('explicit_priorities', [])
            implicit_priorities = claude_analysis.get('implicit_priorities', [])
            all_priorities = list(set(explicit_priorities + implicit_priorities))
            use_case_analysis = claude_analysis.get('use_case_analysis', {})
            use_case = use_case_analysis.get('primary_use')
            brand_prefs = claude_analysis.get('brand_preferences', {})
            brand_preferences = brand_prefs.get('preferred', [])
            excluded_brands = brand_prefs.get('excluded', [])
            # Store Claude's analysis for later use
            enhanced_profile = user_context.copy()
            enhanced_profile['claude_analysis'] = claude_analysis
            enhanced_profile['last_query'] = query
            self.logger.info(f"Claude confidence: {claude_analysis.get('confidence_score', 0):.2f}")
            return ShoppingBrief(
                query=query,
                category=category,
                budget_max=budget_max,
                budget_min=budget_constraints.get('min'),
                priorities=all_priorities,
                use_case=use_case,
                brand_preferences=brand_preferences,
                excluded_brands=excluded_brands,
                user_profile=enhanced_profile
            )
        except Exception as e:
            self.logger.warning(f"Claude analysis failed, using fallback: {str(e)}")
            # Fallback to original logic
            return await self._parse_query_fallback(query, user_id)

    async def _parse_query_fallback(self, query: str, user_id: Optional[str] = None) -> ShoppingBrief:
        """Fallback: original keyword-based parsing logic."""
        query_lower = query.lower()
        budget_max = None
        for pattern in self.budget_patterns:
            match = re.search(pattern, query_lower)
            if match:
                budget_max = float(match.group(1))
                break
        category = "general"
        for cat, keywords in self.category_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                category = cat
                break
        priorities = []
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                priorities.append(priority)
        use_case = None
        use_cases = {
            'running': ['running', 'jogging', 'workout'],
            'work': ['work', 'office', 'meetings', 'calls'],
            'travel': ['travel', 'flights', 'commute'],
            'gaming': ['gaming', 'games'],
            'audiophile': ['audiophile', 'music', 'hi-fi']
        }
        for case, keywords in use_cases.items():
            if any(keyword in query_lower for keyword in keywords):
                use_case = case
                break
        brands = ['apple', 'sony', 'bose', 'sennheiser', 'audio-technica', 'anker', 'jlab']
        brand_preferences = [brand for brand in brands if brand in query_lower]
        return ShoppingBrief(
            query=query,
            category=category,
            budget_max=budget_max,
            priorities=priorities,
            use_case=use_case,
            brand_preferences=brand_preferences,
            user_profile=self.user_preferences.get(user_id, {})
        )
    
    async def _create_execution_plan(self, brief: ShoppingBrief) -> Dict[str, Any]:
        """Create DAG execution plan for other agents"""
        
        tasks = [
            {
                'task_id': 'discovery',
                'agent': 'discovery_agent',
                'action': 'find_products',
                'inputs': {
                    'category': brief.category,
                    'budget_max': brief.budget_max,
                    'brand_preferences': brief.brand_preferences
                },
                'timeout': 15
            },
            {
                'task_id': 'normalization',
                'agent': 'normalization_agent',
                'action': 'normalize_data',
                'depends_on': ['discovery'],
                'timeout': 10
            },
            {
                'task_id': 'scoring',
                'agent': 'scoring_agent',
                'action': 'score_products',
                'inputs': {
                    'priorities': brief.priorities,
                    'use_case': brief.use_case
                },
                'depends_on': ['normalization'],
                'timeout': 15
            },
            {
                'task_id': 'verification',
                'agent': 'verification_agent',
                'action': 'verify_recommendations',
                'inputs': {
                    'budget_max': brief.budget_max,
                    'min_products': 3
                },
                'depends_on': ['scoring'],
                'timeout': 10
            }
        ]
        
        return {
            'plan_id': f"plan_{brief.query[:20]}_{asyncio.get_event_loop().time()}",
            'tasks': tasks,
            'success_criteria': {
                'min_recommendations': 3,
                'within_budget': brief.budget_max is not None,
                'has_justification': True
            }
        }

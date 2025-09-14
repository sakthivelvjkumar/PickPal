import re
import asyncio
from typing import Dict, Any, List, Optional
from textblob import TextBlob
from .base_agent import BaseAgent, EventType
from models.schemas import ShoppingBrief

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
        """Parse natural language query into structured brief"""
        query_lower = query.lower()
        
        # Extract budget
        budget_max = None
        for pattern in self.budget_patterns:
            match = re.search(pattern, query_lower)
            if match:
                budget_max = float(match.group(1))
                break
        
        # Extract category
        category = "general"
        for cat, keywords in self.category_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                category = cat
                break
        
        # Extract priorities
        priorities = []
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                priorities.append(priority)
        
        # Extract use case
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
        
        # Extract brand preferences
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

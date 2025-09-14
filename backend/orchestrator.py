import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from agents.base_agent import EventBus, EventType
from agents.intent_planner import IntentPlannerAgent
from agents.discovery_agent import DiscoveryAgent
from agents.normalization_agent import NormalizationAgent
from agents.scoring_agent import ScoringAgent
from agents.verification_agent import VerificationAgent

class AgentOrchestrator:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.agents = {}
        self.execution_history = []
        
    async def initialize(self):
        """Initialize all 5 agents"""
        self.agents['intent_planner'] = IntentPlannerAgent(self.event_bus)
        self.agents['discovery_agent'] = DiscoveryAgent(self.event_bus)
        self.agents['normalization_agent'] = NormalizationAgent(self.event_bus)
        self.agents['scoring_agent'] = ScoringAgent(self.event_bus)
        self.agents['verification_agent'] = VerificationAgent(self.event_bus)
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.TASK_FAILED, self._handle_task_failure)
        self.event_bus.subscribe(EventType.REPLAN_REQUIRED, self._handle_replan_required)
        
    async def execute_search(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute complete search workflow with all 5 agents"""
        execution_id = f"exec_{datetime.now().isoformat()}"
        start_time = datetime.now()
        
        try:
            # Phase 1: Intent Analysis and Planning
            logging.info("Phase 1: Intent Analysis")
            intent_result = await self.agents['intent_planner'].execute({
                'query': query,
                'user_id': user_id
            })
            
            if intent_result['status'] != 'success':
                raise Exception("Intent analysis failed")
            
            shopping_brief = intent_result['shopping_brief']
            execution_plan = intent_result['execution_plan']
            
            # Phase 2: Product Discovery
            logging.info("Phase 2: Product Discovery")
            discovery_result = await self.agents['discovery_agent'].execute({
                'inputs': {
                    'category': shopping_brief.category,
                    'budget_max': shopping_brief.budget_max,
                    'brand_preferences': shopping_brief.brand_preferences
                }
            })
            
            if discovery_result['status'] != 'success':
                raise Exception("Product discovery failed")
            
            # Phase 3: Data Normalization
            logging.info("Phase 3: Data Normalization")
            normalization_result = await self.agents['normalization_agent'].execute({
                'products': discovery_result['products'],
                'reviews': discovery_result['reviews']
            })
            
            if normalization_result['status'] != 'success':
                raise Exception("Data normalization failed")
            
            # Phase 4: Scoring and Ranking
            logging.info("Phase 4: Scoring and Ranking")
            scoring_result = await self.agents['scoring_agent'].execute({
                'normalized_products': normalization_result['normalized_products'],
                'clean_reviews': normalization_result['clean_reviews'],
                'inputs': {
                    'priorities': shopping_brief.priorities,
                    'use_case': shopping_brief.use_case
                }
            })
            
            if scoring_result['status'] != 'success':
                raise Exception("Product scoring failed")
            
            # Phase 5: Verification and Adaptation
            logging.info("Phase 5: Verification and Adaptation")
            verification_result = await self.agents['verification_agent'].execute({
                'recommendations': scoring_result['recommendations'],
                'inputs': {
                    'budget_max': shopping_brief.budget_max,
                    'min_products': 3
                }
            })
            
            # Handle different verification outcomes
            if verification_result['status'] == 'insufficient_evidence':
                return self._format_insufficient_evidence_response(
                    verification_result, shopping_brief, execution_id, start_time
                )
            
            if verification_result['status'] != 'success':
                raise Exception("Verification failed")
            
            # Format final recommendations
            final_recommendations = []
            for product_score in verification_result['verified_recommendations']:
                final_recommendations.append({
                    'name': product_score.product.name,
                    'brand': product_score.product.brand,
                    'price': product_score.product.price,
                    'rating': product_score.product.rating,
                    'review_count': product_score.product.review_count,
                    'url': product_score.product.url,
                    'image_url': product_score.product.image_url,
                    'overall_score': round(product_score.overall_score, 1),
                    'pros': product_score.pros,
                    'cons': product_score.cons,
                    'justification': product_score.justification
                })
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'recommendations': final_recommendations,
                'query_analysis': {
                    'category': shopping_brief.category,
                    'budget': shopping_brief.budget_max,
                    'priorities': shopping_brief.priorities,
                    'use_case': shopping_brief.use_case
                },
                'execution_summary': {
                    'execution_id': execution_id,
                    'processing_time': processing_time,
                    'agents_executed': ['intent_planner', 'discovery_agent', 'normalization_agent', 'scoring_agent', 'verification_agent'],
                    'total_products_analyzed': len(discovery_result['products']),
                    'products_after_normalization': len(normalization_result['normalized_products']),
                    'final_recommendations': len(final_recommendations),
                    'issues_found': len(verification_result.get('issues_found', [])),
                    'data_quality_score': normalization_result['metadata']['quality_metrics']['data_quality_score']
                }
            }
            
        except Exception as e:
            logging.error(f"Search execution failed: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'error',
                'error': str(e),
                'recommendations': [],
                'query_analysis': {},
                'execution_summary': {
                    'execution_id': execution_id,
                    'processing_time': processing_time,
                    'error_occurred': True
                }
            }
    
    def _format_insufficient_evidence_response(self, verification_result, shopping_brief, execution_id, start_time):
        """Format response when insufficient evidence is found"""
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Still format any recommendations we do have
        limited_recommendations = []
        for product_score in verification_result['verified_recommendations']:
            limited_recommendations.append({
                'name': product_score.product.name,
                'brand': product_score.product.brand,
                'price': product_score.product.price,
                'rating': product_score.product.rating,
                'review_count': product_score.product.review_count,
                'url': product_score.product.url,
                'image_url': product_score.product.image_url,
                'overall_score': round(product_score.overall_score, 1),
                'pros': product_score.pros,
                'cons': product_score.cons,
                'justification': product_score.justification
            })
        
        return {
            'status': 'insufficient_evidence',
            'recommendations': limited_recommendations,
            'limitation_reason': verification_result.get('limitation_reason', 'Insufficient evidence'),
            'recommendation': verification_result.get('recommendation', 'Try adjusting search criteria'),
            'query_analysis': {
                'category': shopping_brief.category,
                'budget': shopping_brief.budget_max,
                'priorities': shopping_brief.priorities,
                'use_case': shopping_brief.use_case
            },
            'execution_summary': {
                'execution_id': execution_id,
                'processing_time': processing_time,
                'agents_executed': ['intent_planner', 'discovery_agent', 'normalization_agent', 'scoring_agent', 'verification_agent'],
                'issues_found': verification_result.get('issues_found', [])
            }
        }
    
    async def _handle_task_failure(self, event):
        """Handle agent task failures with retry logic"""
        logging.warning(f"Agent {event.agent_id} task failed: {event.data}")
        
        # Implement retry logic based on failure type
        if event.data.get('task') == 'product_discovery':
            # Could trigger alternative data sources
            logging.info("Could retry discovery with alternative sources")
        elif event.data.get('task') == 'product_scoring':
            # Could use simplified scoring
            logging.info("Could fallback to simplified scoring")
        
    async def _handle_replan_required(self, event):
        """Handle requests for replanning"""
        logging.info(f"Replan requested by {event.agent_id}: {event.data}")
        
        # Could trigger re-execution with adjusted parameters
        reason = event.data.get('reason', 'unknown')
        if reason == 'insufficient_verified_recommendations':
            logging.info("Could relax verification constraints and retry")
    
    def get_agent_status(self) -> Dict[str, str]:
        """Get status of all agents"""
        return {agent_id: agent.state for agent_id, agent in self.agents.items()}
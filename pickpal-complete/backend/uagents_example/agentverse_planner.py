"""
MyPickPal Planner Agent - Agentverse Compatible
Main orchestrator agent that coordinates the shopping pipeline for Agentverse
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from uagents import Agent, Context, Protocol
from uagents.setup import fund_agent_if_low

# Import existing planner logic
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from planner.agent import PlannerAgent as CorePlannerAgent
from common.messages import ShoppingBrief

# Agentverse message models
class AgentverseShoppingGoal(BaseModel):
    """Natural language shopping goal for Agentverse"""
    goal_id: str = Field(description="Unique goal identifier")
    user_intent: str = Field(description="Natural language shopping intent")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    user_address: str = Field(description="Address of requesting user/agent")
    priority: str = Field(default="normal", description="Priority level: low, normal, high")

class AgentverseShoppingResult(BaseModel):
    """Complete shopping result for Agentverse"""
    goal_id: str = Field(description="Goal identifier")
    success: bool = Field(description="Whether goal was achieved")
    intent_understood: str = Field(description="How the intent was interpreted")
    execution_plan: List[str] = Field(description="Steps taken to fulfill the goal")
    recommendations: List[Dict[str, Any]] = Field(description="Product recommendations")
    total_found: int = Field(description="Total products discovered")
    execution_time_ms: int = Field(description="Total execution time")
    confidence_score: float = Field(description="Confidence in recommendations (0-1)")
    next_actions: List[str] = Field(description="Suggested next steps for user")
    message: str = Field(description="Human-readable summary")

# Create Agentverse-compatible agent
planner_agent = Agent(
    name="MyPickPal-Planner",
    seed="mypickpal_planner_agentverse_seed_67890",
    port=8001,
    endpoint=["http://localhost:8001/submit"]
)

# Initialize core planner
core_planner = CorePlannerAgent()

# Agentverse Planner Protocol
planner_protocol = Protocol("MyPickPal-Planner", version="1.0")

@planner_agent.on_event("startup")
async def setup_agentverse_planner(ctx: Context):
    """Initialize planner agent for Agentverse"""
    ctx.logger.info("MyPickPal Planner Agent starting for Agentverse...")
    ctx.logger.info(f"Agent address: {planner_agent.address}")
    ctx.logger.info(f"Wallet address: {planner_agent.wallet.address()}")
    
    # Fund agent if needed
    try:
        await fund_agent_if_low(planner_agent.wallet.address())
        ctx.logger.info("Agent funded successfully")
    except Exception as e:
        ctx.logger.warning(f"Could not auto-fund agent: {e}")
    
    # Initialize core planner components
    await core_planner.initialize()
    ctx.logger.info("Core planner system initialized")
    
    # Log service capabilities for Agentverse
    ctx.logger.info("Available services:")
    ctx.logger.info("- Intent Understanding: Parse natural language shopping goals")
    ctx.logger.info("- Multi-step Planning: Break goals into executable steps")
    ctx.logger.info("- Pipeline Orchestration: Coordinate Discovery → Normalize → Rank → Verify")
    ctx.logger.info("- Outcome Verification: Ensure goals are met with quality checks")
    ctx.logger.info("- Adaptive Execution: Retry and adapt when initial attempts fail")

@planner_protocol.on_message(model=AgentverseShoppingGoal)
async def handle_shopping_goal(ctx: Context, sender: str, msg: AgentverseShoppingGoal):
    """Handle natural language shopping goals from Agentverse"""
    start_time = asyncio.get_event_loop().time()
    
    ctx.logger.info(f"Received shopping goal {msg.goal_id} from {sender}")
    ctx.logger.info(f"Intent: {msg.user_intent}")
    ctx.logger.info(f"Priority: {msg.priority}")
    
    execution_plan = []
    
    try:
        # Step 1: Intent Understanding
        execution_plan.append("Analyzing natural language intent")
        ctx.logger.info("Step 1: Understanding user intent...")
        
        # Parse intent and extract constraints
        constraints = await parse_shopping_intent(msg.user_intent, msg.context)
        intent_summary = f"Looking for {constraints.get('category', 'products')} with budget ${constraints.get('max_price', 'flexible')}"
        
        execution_plan.append(f"Intent understood: {intent_summary}")
        
        # Step 2: Multi-step Planning
        execution_plan.append("Creating execution plan")
        ctx.logger.info("Step 2: Creating multi-step execution plan...")
        
        # Build shopping brief
        shopping_brief = ShoppingBrief(
            request_id=msg.goal_id,
            query=msg.user_intent,
            category=constraints.get('category', 'general'),
            use_case=constraints.get('use_case', 'general'),
            constraints=constraints,
            weights={"rating": 0.4, "sentiment": 0.3, "recency": 0.2, "helpfulness": 0.1},
            success={"k": 5, "diversity": True, "min_reviews": 3}
        )
        
        execution_plan.append("Shopping brief created with constraints and success criteria")
        
        # Step 3: Execute Pipeline
        execution_plan.append("Executing discovery pipeline")
        ctx.logger.info("Step 3: Executing coordinated pipeline...")
        
        # Use core planner to orchestrate the full pipeline
        result = await core_planner.handle_user_goal(
            query=msg.user_intent,
            constraints=constraints,
            request_id=msg.goal_id
        )
        
        execution_plan.append(f"Pipeline completed: {result.get('total_found', 0)} products found")
        
        # Step 4: Outcome Verification
        execution_plan.append("Verifying outcomes meet user goals")
        ctx.logger.info("Step 4: Verifying outcomes...")
        
        # Calculate confidence based on results
        confidence_score = calculate_confidence_score(result)
        execution_plan.append(f"Confidence score: {confidence_score:.2f}")
        
        # Step 5: Next Actions
        next_actions = generate_next_actions(result, msg.user_intent, confidence_score)
        execution_plan.append("Generated next action recommendations")
        
        # Calculate execution time
        execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Create successful response
        response = AgentverseShoppingResult(
            goal_id=msg.goal_id,
            success=result.get('success', False),
            intent_understood=intent_summary,
            execution_plan=execution_plan,
            recommendations=result.get('recommendations', []),
            total_found=result.get('total_found', 0),
            execution_time_ms=execution_time,
            confidence_score=confidence_score,
            next_actions=next_actions,
            message=f"Successfully fulfilled shopping goal: {len(result.get('recommendations', []))} recommendations found"
        )
        
        ctx.logger.info(f"Goal {msg.goal_id} completed successfully in {execution_time}ms")
        
        # Send response back to requester
        await ctx.send(sender, response)
        
    except Exception as e:
        ctx.logger.error(f"Goal execution failed for {msg.goal_id}: {e}")
        
        execution_plan.append(f"Execution failed: {str(e)}")
        execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Send error response
        error_response = AgentverseShoppingResult(
            goal_id=msg.goal_id,
            success=False,
            intent_understood="Failed to parse intent",
            execution_plan=execution_plan,
            recommendations=[],
            total_found=0,
            execution_time_ms=execution_time,
            confidence_score=0.0,
            next_actions=["Please rephrase your shopping goal", "Try being more specific about what you're looking for"],
            message=f"Goal execution failed: {str(e)}"
        )
        
        await ctx.send(sender, error_response)

async def parse_shopping_intent(intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Parse natural language shopping intent into structured constraints"""
    constraints = {}
    intent_lower = intent.lower()
    
    # Extract price constraints
    import re
    price_patterns = [
        r'under \$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'below \$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'less than \$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'budget of \$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'\$(\d+(?:,\d{3})*(?:\.\d{2})?) or less'
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, intent_lower)
        if match:
            price_str = match.group(1).replace(',', '')
            constraints['max_price'] = float(price_str)
            break
    
    # Extract category
    categories = {
        'wireless_earbuds': ['earbuds', 'wireless earbuds', 'airpods', 'bluetooth earbuds'],
        'laptops': ['laptop', 'notebook', 'gaming laptop', 'macbook'],
        'smartphones': ['phone', 'smartphone', 'iphone', 'android'],
        'headphones': ['headphones', 'headset', 'over-ear'],
        'tablets': ['tablet', 'ipad', 'android tablet'],
        'smartwatch': ['watch', 'smartwatch', 'apple watch', 'fitness tracker'],
        'furniture': ['desk', 'chair', 'table', 'standing desk', 'office chair']
    }
    
    for category, keywords in categories.items():
        if any(keyword in intent_lower for keyword in keywords):
            constraints['category'] = category
            break
    
    # Extract use case
    use_cases = {
        'work': ['work', 'office', 'business', 'professional', 'productivity'],
        'gaming': ['gaming', 'games', 'esports', 'streaming'],
        'fitness': ['fitness', 'workout', 'exercise', 'running', 'gym'],
        'travel': ['travel', 'portable', 'lightweight', 'compact'],
        'home': ['home', 'house', 'family', 'personal']
    }
    
    for use_case, keywords in use_cases.items():
        if any(keyword in intent_lower for keyword in keywords):
            constraints['use_case'] = use_case
            break
    
    # Extract rating requirements
    if 'highly rated' in intent_lower or 'best rated' in intent_lower:
        constraints['min_rating'] = 4.5
    elif 'good rating' in intent_lower or 'well rated' in intent_lower:
        constraints['min_rating'] = 4.0
    
    # Add context constraints
    constraints.update(context)
    
    return constraints

def calculate_confidence_score(result: Dict[str, Any]) -> float:
    """Calculate confidence score based on execution results"""
    if not result.get('success', False):
        return 0.0
    
    recommendations = result.get('recommendations', [])
    if not recommendations:
        return 0.1
    
    # Base confidence on number of recommendations and their quality
    num_recs = len(recommendations)
    avg_rating = sum(rec.get('rating', 0) for rec in recommendations) / num_recs if num_recs > 0 else 0
    
    # Confidence factors
    quantity_factor = min(num_recs / 5.0, 1.0)  # Ideal: 5+ recommendations
    quality_factor = avg_rating / 5.0  # Based on average rating
    
    return (quantity_factor * 0.4 + quality_factor * 0.6)

def generate_next_actions(result: Dict[str, Any], original_intent: str, confidence: float) -> List[str]:
    """Generate suggested next actions for the user"""
    next_actions = []
    
    if confidence >= 0.8:
        next_actions.extend([
            "Review the recommended products",
            "Compare prices and features",
            "Check availability and shipping options"
        ])
    elif confidence >= 0.5:
        next_actions.extend([
            "Consider refining your search criteria",
            "Look at additional product options",
            "Read more detailed reviews"
        ])
    else:
        next_actions.extend([
            "Try a more specific search query",
            "Adjust your budget or requirements",
            "Consider alternative product categories"
        ])
    
    # Add intent-specific actions
    if 'budget' in original_intent.lower() or '$' in original_intent:
        next_actions.append("Set up price alerts for better deals")
    
    if 'best' in original_intent.lower():
        next_actions.append("Compare with premium alternatives")
    
    return next_actions

# Chat Protocol for ASI:One integration
chat_protocol = Protocol("Chat", version="1.0")

class ChatMessage(BaseModel):
    """Chat message for ASI:One integration"""
    message: str = Field(description="User message")
    session_id: str = Field(description="Chat session identifier")

class ChatResponse(BaseModel):
    """Chat response for ASI:One"""
    message: str = Field(description="Agent response")
    session_id: str = Field(description="Chat session identifier")
    action_taken: bool = Field(description="Whether an action was performed")
    goal_created: bool = Field(default=False, description="Whether a shopping goal was created")

@chat_protocol.on_message(model=ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """Handle chat messages from ASI:One"""
    ctx.logger.info(f"Chat message from {sender}: {msg.message}")
    
    # Detect if this is a shopping goal
    shopping_indicators = [
        "find", "search", "buy", "purchase", "recommend", "best", "need", "want", 
        "looking for", "help me", "suggest", "advice", "compare"
    ]
    
    is_shopping_goal = any(indicator in msg.message.lower() for indicator in shopping_indicators)
    
    if is_shopping_goal:
        # Convert chat to shopping goal
        goal_id = f"chat_goal_{msg.session_id}_{uuid.uuid4().hex[:8]}"
        
        shopping_goal = AgentverseShoppingGoal(
            goal_id=goal_id,
            user_intent=msg.message,
            context={"source": "chat", "session_id": msg.session_id},
            user_address=sender,
            priority="normal"
        )
        
        # Process the shopping goal
        await handle_shopping_goal(ctx, sender, shopping_goal)
        
        # Send chat response
        chat_response = ChatResponse(
            message=f"I understand you're looking for: '{msg.message}'. Let me create a comprehensive shopping plan and find the best options for you!",
            session_id=msg.session_id,
            action_taken=True,
            goal_created=True
        )
        
    else:
        # General chat response
        chat_response = ChatResponse(
            message="I'm MyPickPal's Planning Agent! I can help you achieve your shopping goals. Try telling me what you're looking for, like 'I need a gaming laptop under $1200' or 'Find me the best wireless earbuds for work'.",
            session_id=msg.session_id,
            action_taken=False,
            goal_created=False
        )
    
    await ctx.send(sender, chat_response)

# Include protocols
planner_agent.include(planner_protocol)
planner_agent.include(chat_protocol)

if __name__ == "__main__":
    print("Starting MyPickPal Planner Agent for Agentverse...")
    print(f"Agent address: {planner_agent.address}")
    print("Services available:")
    print("- Natural Language Intent Understanding")
    print("- Multi-step Execution Planning")
    print("- Pipeline Orchestration (Discovery → Normalize → Rank → Verify)")
    print("- Outcome Verification & Adaptation")
    print("- Chat Protocol for ASI:One")
    planner_agent.run()

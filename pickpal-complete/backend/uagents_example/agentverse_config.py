"""
Agentverse Configuration and Registration
Configuration for deploying MyPickPal agents to Agentverse marketplace
"""

import os
from typing import Dict, Any

# Agentverse Configuration
AGENTVERSE_CONFIG = {
    "network": "fetchai-testnet",  # or "fetchai-mainnet" for production
    "agentverse_url": "https://agentverse.ai",
    "registration_endpoint": "https://agentverse.ai/api/v1/agents/register",
    "marketplace_url": "https://agentverse.ai/marketplace"
}

# Agent Metadata for Agentverse Registration
DISCOVERY_AGENT_METADATA = {
    "name": "MyPickPal Discovery Agent",
    "description": "AI-powered product discovery agent that searches Amazon, Reddit, and review blogs to find the best products based on natural language queries.",
    "version": "1.0.0",
    "author": "MyPickPal Team",
    "tags": ["shopping", "ecommerce", "product-discovery", "ai", "recommendations"],
    "category": "Shopping & Commerce",
    "capabilities": [
        "Multi-source product search (Amazon, Reddit, Review Blogs)",
        "Natural language query processing",
        "Evidence-based filtering and ranking",
        "Duplicate detection and deduplication",
        "Real-time price and availability checking"
    ],
    "protocols": ["MyPickPal-Discovery", "Chat"],
    "endpoints": {
        "discovery": "/discover",
        "chat": "/chat",
        "health": "/health"
    },
    "pricing": {
        "model": "pay-per-use",
        "base_fee": 0.001,  # FET tokens per request
        "currency": "FET"
    },
    "service_level": {
        "availability": "99.9%",
        "response_time_ms": 2000,
        "max_concurrent_requests": 100
    }
}

PLANNER_AGENT_METADATA = {
    "name": "MyPickPal Planning Agent",
    "description": "Intelligent shopping planner that understands natural language goals and orchestrates multi-step execution to deliver personalized product recommendations.",
    "version": "1.0.0",
    "author": "MyPickPal Team",
    "tags": ["shopping", "planning", "ai", "orchestration", "intent-understanding"],
    "category": "Shopping & Commerce",
    "capabilities": [
        "Natural language intent understanding",
        "Multi-step execution planning",
        "Pipeline orchestration (Discovery → Normalize → Rank → Verify)",
        "Outcome verification and adaptation",
        "Confidence scoring and next-action recommendations"
    ],
    "protocols": ["MyPickPal-Planner", "Chat"],
    "endpoints": {
        "plan": "/plan",
        "chat": "/chat",
        "status": "/status",
        "health": "/health"
    },
    "pricing": {
        "model": "pay-per-goal",
        "base_fee": 0.005,  # FET tokens per shopping goal
        "currency": "FET"
    },
    "service_level": {
        "availability": "99.9%",
        "response_time_ms": 5000,
        "max_concurrent_requests": 50
    }
}

# Environment Configuration
def get_agentverse_config() -> Dict[str, Any]:
    """Get Agentverse configuration from environment variables"""
    return {
        "network": os.getenv("AGENTVERSE_NETWORK", "fetchai-testnet"),
        "api_key": os.getenv("AGENTVERSE_API_KEY"),
        "agent_seed": os.getenv("AGENT_SEED"),
        "public_endpoint": os.getenv("PUBLIC_ENDPOINT", "http://localhost"),
        "enable_chat_protocol": os.getenv("ENABLE_CHAT", "true").lower() == "true",
        "enable_marketplace": os.getenv("ENABLE_MARKETPLACE", "true").lower() == "true"
    }

# Registration payload templates
def create_registration_payload(agent_type: str, agent_address: str, public_endpoint: str) -> Dict[str, Any]:
    """Create registration payload for Agentverse"""
    
    metadata = DISCOVERY_AGENT_METADATA if agent_type == "discovery" else PLANNER_AGENT_METADATA
    
    return {
        "agent_address": agent_address,
        "metadata": metadata,
        "endpoints": {
            "primary": f"{public_endpoint}/submit",
            "health": f"{public_endpoint}/health",
            "metrics": f"{public_endpoint}/metrics"
        },
        "network": AGENTVERSE_CONFIG["network"],
        "status": "active",
        "auto_discovery": True,
        "marketplace_listing": True
    }

# Service descriptions for marketplace
SERVICE_DESCRIPTIONS = {
    "discovery": {
        "title": "AI Product Discovery",
        "short_description": "Find the best products from multiple sources using natural language",
        "long_description": """
        The MyPickPal Discovery Agent is an advanced AI system that helps you find the perfect products by searching across multiple sources including Amazon, Reddit discussions, and expert review blogs.

        **Key Features:**
        - 🔍 Multi-source search across Amazon, Reddit, and review blogs
        - 🧠 Natural language query understanding
        - 📊 Evidence-based filtering and quality scoring
        - 🔄 Automatic deduplication across sources
        - ⚡ Real-time availability and pricing

        **Perfect for:**
        - Finding products based on natural language descriptions
        - Comparing options across multiple platforms
        - Getting comprehensive product information
        - Making informed purchasing decisions

        **Example queries:**
        - "Find wireless earbuds under $150 for work"
        - "Best gaming laptop with good battery life"
        - "Recommend a standing desk for home office"
        """,
        "use_cases": [
            "E-commerce product search",
            "Price comparison",
            "Product research",
            "Shopping automation",
            "Recommendation systems"
        ],
        "demo_queries": [
            "Find wireless earbuds under $100",
            "Best laptop for programming",
            "Recommend a coffee maker under $200"
        ]
    },
    "planner": {
        "title": "AI Shopping Planner",
        "short_description": "Turn shopping goals into actionable plans with personalized recommendations",
        "long_description": """
        The MyPickPal Planning Agent transforms your shopping intentions into comprehensive, actionable plans. It understands what you really want to achieve and orchestrates the entire process to deliver perfect recommendations.

        **Key Features:**
        - 🎯 Natural language goal understanding
        - 📋 Multi-step execution planning
        - 🔄 Pipeline orchestration and coordination
        - ✅ Outcome verification and quality assurance
        - 🎯 Confidence scoring and next-action recommendations

        **Perfect for:**
        - Complex shopping decisions
        - Budget-conscious shopping
        - Research-heavy purchases
        - Gift recommendations
        - Business procurement

        **Example goals:**
        - "I need a complete home office setup under $2000"
        - "Find the best tech gifts for a teenager"
        - "Help me upgrade my gaming setup within budget"
        """,
        "use_cases": [
            "Personal shopping assistance",
            "Business procurement",
            "Gift planning",
            "Budget optimization",
            "Product comparison"
        ],
        "demo_goals": [
            "Set up a home gym under $1000",
            "Find the perfect laptop for college",
            "Plan a complete kitchen upgrade"
        ]
    }
}

# Chat Protocol Configuration for ASI:One
CHAT_PROTOCOL_CONFIG = {
    "protocol_name": "Chat",
    "version": "1.0",
    "supported_features": [
        "natural_language_processing",
        "intent_recognition",
        "action_execution",
        "context_awareness",
        "session_management"
    ],
    "response_types": [
        "informational",
        "action_confirmation",
        "product_recommendations",
        "error_handling"
    ],
    "max_session_duration": 3600,  # 1 hour
    "max_message_length": 1000
}

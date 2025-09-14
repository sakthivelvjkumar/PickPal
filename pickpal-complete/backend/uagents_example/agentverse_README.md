# MyPickPal Agentverse Integration

Complete conversion of MyPickPal agents for Agentverse marketplace deployment with Chat Protocol support for ASI:One integration.

## 🚀 Quick Start

### 1. Deploy to Agentverse
```bash
# Set environment variables
export PUBLIC_ENDPOINT=https://your-domain.com
export AGENTVERSE_NETWORK=fetchai-testnet

# Run deployment script
python agentverse_deployment.py
```

### 2. Start Agents
```bash
# Terminal 1 - Discovery Agent
python agentverse_discovery.py

# Terminal 2 - Planner Agent  
python agentverse_planner.py
```

## 🤖 Agents Overview

### Discovery Agent (`agentverse_discovery.py`)
**Purpose:** AI-powered product discovery from multiple sources
- **Address:** `agent1qw8s7d9k2j3h4g5f6d7s8a9z0x1c2v3b4n5m6` (example)
- **Protocols:** `MyPickPal-Discovery`, `Chat`
- **Capabilities:**
  - Multi-source search (Amazon, Reddit, Review Blogs)
  - Natural language query processing
  - Evidence-based filtering and deduplication
  - Real-time availability checking

### Planner Agent (`agentverse_planner.py`)
**Purpose:** Intent understanding and multi-step execution planning
- **Address:** `agent1qf7g8h9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z` (example)
- **Protocols:** `MyPickPal-Planner`, `Chat`
- **Capabilities:**
  - Natural language intent parsing
  - Multi-step execution planning
  - Pipeline orchestration
  - Outcome verification and adaptation

## 📡 Message Protocols

### Discovery Protocol
```python
# Request
AgentverseShoppingRequest(
    request_id="req_123",
    user_query="wireless earbuds under $150",
    constraints={"max_price": 150.0},
    user_address="user_agent_address"
)

# Response
AgentverseDiscoveryResponse(
    request_id="req_123",
    success=True,
    products_found=5,
    products=[...],
    sources_used=["amazon", "reddit"],
    execution_time_ms=1500,
    message="Successfully discovered 5 products"
)
```

### Planning Protocol
```python
# Request
AgentverseShoppingGoal(
    goal_id="goal_456",
    user_intent="I need a complete home office setup under $2000",
    context={},
    user_address="user_agent_address",
    priority="high"
)

# Response
AgentverseShoppingResult(
    goal_id="goal_456",
    success=True,
    intent_understood="Complete home office setup with $2000 budget",
    execution_plan=[...],
    recommendations=[...],
    confidence_score=0.85,
    next_actions=[...]
)
```

### Chat Protocol (ASI:One Integration)
```python
# Chat Message
ChatMessage(
    message="Find me the best gaming laptop under $1200",
    session_id="chat_session_789"
)

# Chat Response
ChatResponse(
    message="I'll help you find the perfect gaming laptop! Let me search...",
    session_id="chat_session_789",
    action_taken=True,
    goal_created=True
)
```

## 🌐 Agentverse Features

### Service Registration
- **Discovery Agent:** Product discovery and search services
- **Planner Agent:** Intent understanding and execution planning
- **Marketplace Listing:** Both agents listed in Agentverse marketplace
- **Service Discovery:** Other agents can find and use these services

### Pricing Model
- **Discovery:** 0.001 FET per search request
- **Planning:** 0.005 FET per shopping goal
- **Chat:** Free for basic interactions

### Service Level Agreements
- **Availability:** 99.9% uptime
- **Response Time:** <2s for discovery, <5s for planning
- **Concurrent Requests:** 100 for discovery, 50 for planning

## 🔧 Configuration Files

### `agentverse_config.py`
- Agent metadata and service descriptions
- Pricing and SLA configuration
- Chat Protocol settings
- Registration payloads

### `agentverse_deployment.py`
- Automated deployment script
- Registration with Agentverse
- Health checks and monitoring
- Deployment instructions generator

## 🎯 ASI:One Integration

### Chat Protocol Support
Both agents implement the Chat Protocol for seamless integration with ASI:One:

```python
@chat_protocol.on_message(model=ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    # Natural language processing
    # Intent detection
    # Action execution
    # Response generation
```

### Natural Language Examples
- **Discovery:** "Find wireless earbuds under $100"
- **Planning:** "I need a complete gaming setup within budget"
- **Chat:** "Help me find the best laptop for programming"

## 🚀 Deployment Options

### Local Development
```bash
python agentverse_discovery.py  # Port 8000
python agentverse_planner.py    # Port 8001
```

### Production Deployment
```bash
# Docker deployment
docker-compose up -d

# Cloud deployment (AWS/GCP/Azure)
# See deployment_instructions.md
```

### Agentverse Registration
```bash
# Automated registration
python agentverse_deployment.py

# Manual registration via Agentverse UI
# Visit: https://agentverse.ai/agents/register
```

## 📊 Monitoring & Analytics

### Health Endpoints
- `GET /health` - Agent health status
- `GET /metrics` - Performance metrics
- `GET /status` - Service status

### Logging
- Structured logging for all requests
- Request tracing and performance monitoring
- Error tracking and alerting

## 🔐 Security & Authentication

### Agent Identity
- Cryptographic agent addresses
- Secure message signing
- Identity verification

### API Security
- Rate limiting
- Input validation
- Error handling

## 💰 Economic Model

### Token Economics
- Agents earn FET tokens for services
- Pay-per-use pricing model
- Automatic payment processing

### Revenue Sharing
- Agent operators earn from service usage
- Agentverse marketplace fees
- Transparent pricing

## 🛠️ Development

### Adding New Capabilities
1. Extend message protocols
2. Add new service endpoints
3. Update agent metadata
4. Re-register with Agentverse

### Testing
```bash
# Unit tests
python -m pytest tests/

# Integration tests
python test_agentverse_integration.py

# Load testing
python load_test_agents.py
```

## 📚 Resources

- **Agentverse Documentation:** https://docs.agentverse.ai
- **uAgents Framework:** https://github.com/fetchai/uAgents
- **ASI:One Integration:** https://docs.fetch.ai/asi-one
- **Chat Protocol Spec:** https://docs.fetch.ai/protocols/chat

## 🆘 Support

- **Issues:** Create GitHub issues for bugs
- **Discord:** Join Fetch.ai Discord for community support
- **Documentation:** Check Agentverse docs for latest updates

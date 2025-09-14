# Backend - AI Shopping Assistant

This backend implements a modular, agent-based architecture for an AI-powered shopping assistant using FastAPI. Each agent is responsible for a specific part of the product recommendation workflow, from intent parsing to product discovery, normalization, scoring, and verification.

## Project Structure

```
backend/
│   config.py            # Application configuration using Pydantic settings
│   main.py              # FastAPI application entry point
│   orchestrator.py      # Orchestrates agent workflow and manages agent lifecycle
│
├── agents/
│   base_agent.py        # Abstract base class and event bus for all agents
│   discovery_agent.py   # Discovers products and generates mock data
│   intent_planner.py    # Parses user queries and creates execution plans
│   normalization_agent.py # Normalizes product/review data and enriches metadata
│   scoring_agent.py     # Scores products based on multiple criteria
│   verification_agent.py # Verifies recommendations and applies business rules
│
├── models/
│   __init__.py          # Imports all model schemas
│   schemas.py           # Data models for products, reviews, API requests/responses
│
├── services/            # (Reserved for future business logic/services)
├── utils/               # (Reserved for utility/helper functions)
```

## File Documentation

### config.py
- **Purpose:** Centralized configuration using Pydantic's BaseSettings (from pydantic-settings).
- **Usage:** Stores agent timeouts, scoring weights, and other global settings. Reads from `.env` if present.

### main.py
- **Purpose:** FastAPI application entry point.
- **Usage:** Sets up API routes, CORS, logging, and initializes the agent orchestrator on startup.
- **Endpoints:**
  - `/search` (POST): Main endpoint for product search and recommendations.
  - `/health` (GET): Health check endpoint.

### orchestrator.py
- **Purpose:** Manages the lifecycle and coordination of all agents.
- **Usage:** Initializes agents, executes the full search workflow, and aggregates results.

### agents/base_agent.py
- **Purpose:** Defines the abstract base class for all agents and the event bus system.
- **Usage:** All agents inherit from `BaseAgent` and use the event bus for communication and event handling.

### agents/intent_planner.py
- **Purpose:** Parses user queries to extract structured shopping intents and creates an execution plan for downstream agents.
- **Usage:** Implements `IntentPlannerAgent` which analyzes queries for category, budget, priorities, use case, and brand preferences.

### agents/discovery_agent.py
- **Purpose:** Discovers products and generates mock product and review data for demonstration/testing.
- **Usage:** Implements `DiscoveryAgent` which returns a list of products and reviews based on the parsed query.

### agents/normalization_agent.py
- **Purpose:** Normalizes product and review data, removes duplicates, detects spam, and enriches metadata.
- **Usage:** Implements `NormalizationAgent` for data cleaning and metadata enrichment.

### agents/scoring_agent.py
- **Purpose:** Scores products based on multiple aspects (e.g., rating, sentiment, recency, helpfulness, verified purchase).
- **Usage:** Implements `ScoringAgent` to assign scores and rank products for recommendations.

### agents/verification_agent.py
- **Purpose:** Verifies the final recommendations, ensuring they meet business rules and user constraints.
- **Usage:** Implements `VerificationAgent` for post-processing and validation of recommendations.

### models/schemas.py
- **Purpose:** Defines all data models (dataclasses and Pydantic models) for products, reviews, API requests, and responses.
- **Usage:** Used throughout the backend for type safety and data validation.

### models/__init__.py
- **Purpose:** Imports all schemas for easy access.
- **Usage:** Allows `from models import *` to work as expected.

### services/
- **Purpose:** (Reserved) For future business logic, integrations, or service classes.

### utils/
- **Purpose:** (Reserved) For utility/helper functions shared across the backend.

---

## Getting Started

1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   pip install pydantic-settings
   ```
2. Start the server:
   ```powershell
   cd backend
   uvicorn main:app --reload
   ```
3. Test the API:
   Use curl or Postman to POST to `http://localhost:8000/search` with a JSON body.

---

## Notes
- This backend is modular and easily extensible—add new agents or services as needed.
- The current product discovery uses mock data for demonstration. Integrate real data sources as needed.
- For Windows users, use `curl.exe` or PowerShell's `Invoke-WebRequest` for API testing.

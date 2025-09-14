# Demo Scenarios for AI Shopping Agent

## Scenario 1: Happy Path - Wireless Earbuds

**Input Query:** "Best wireless earbuds under $150 for running"

**Expected Flow:**
1. Planner parses query and detects category: wireless_earbuds
2. Discovery finds 5 earbud products from mock data
3. Normalizer deduplicates and enriches with signals
4. Ranker scores products and extracts pros/cons
5. Verifier checks constraints (budget $150, use case: running)
6. Returns top 3 recommendations with scores and explanations

**Expected Output:**
- 3 product cards with names, prices, ratings, pros/cons
- Overall scores based on rating, sentiment, recency, helpfulness
- Clear explanations of why each product was recommended

## Scenario 2: Budget Constraint Failure → Adaptation

**Input Query:** "Best standing desk under $300"

**Expected Flow:**
1. Discovery finds standing desk products
2. Some products exceed $300 budget
3. Verifier fails budget check
4. Planner adapts by filtering out expensive products
5. Re-ranks remaining products
6. Returns adapted results within budget

**Expected Output:**
- Products all under $300
- Adaptation noted in logs
- Still provides 3 recommendations if possible

## Scenario 3: Low Evidence → Rediscovery

**Input Query:** "Premium laptop with minimum 200 reviews"

**Expected Flow:**
1. Discovery finds laptop products
2. Mock data has fewer than 200 reviews per product
3. Verifier fails evidence threshold check
4. Planner adapts by lowering min_reviews requirement
5. Re-ranks with adjusted criteria
6. Returns results with available evidence

**Expected Output:**
- Products with available review data
- Explanation of evidence threshold adjustment
- Quality scores based on available data

## Testing Commands

```bash
# Start the server
cd /Users/edwinma/Desktop/Dev/MyPickPal/pickpal-complete/backend
uvicorn app.main:app --reload --port 8000

# Test API endpoints
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "best wireless earbuds under 150 for running"}'

curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "standing desk under 300", "max_price": 300}'

curl -X GET "http://localhost:8000/categories"
```

## Expected Agent Interactions

1. **Planner** orchestrates the entire flow
2. **Discovery** loads mock data and filters by constraints
3. **Normalizer** deduplicates similar products and calculates signals
4. **Ranker** applies composite scoring and generates pros/cons
5. **Verifier** checks results against constraints and success criteria
6. **Clarifier** (optional) asks for missing information

## Key Features to Demonstrate

- **Request ID tracing** through all agents
- **Composite scoring** with multiple factors
- **Aspect-based pros/cons** extraction
- **Constraint verification** and adaptation
- **Diversity consideration** in rankings
- **Structured logging** with agent correlation

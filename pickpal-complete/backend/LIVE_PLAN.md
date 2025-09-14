Goals

Ship an MVP that: (1) accepts a shopping query, (2) asks ≤2 clarifying questions if needed, (3) discovers candidates, (4) normalizes/enriches, (5) ranks & extracts pros/cons, (6) verifies constraints & adapts, (7) returns 3 cards with score + reasons.

Agents are message-driven, idempotent, and composable (Agentverse-ready).

Milestones

M1 (Core skeleton): common schemas, runner, mock data, logging.

M2 (Execution chain): Discovery → Normalizer → Ranker working on mocks.

M3 (Agentic loop): Planner + Clarifier + Verifier + adaptation.

M4 (Demo polish): chat entrypoint, pretty cards JSON, one “failure → replan” showpiece.

M5 (Fetch.ai): register agents on Agentverse, implement Chat Protocol shim.

Repo structure
ai-shopping/
  LIVE_PLAN.md
  README.md
  .env.example
  requirements.txt
  pyproject.toml
  src/
    common/
      messages.py        # pydantic models for all agent I/O
      bus.py             # lightweight pub/sub + tracing IDs
      utils.py           # logging, timers, retries, text utils
      scoring.py         # score math, decay, zscores
      aspects.py         # aspect extraction helpers (regex/keywords)
      mocks/
        reviews_earbuds.json
        reviews_desks.json
    planner/
      agent.py
      policy.py          # planning rules, success criteria, DAG
      memory.py          # session prefs store (in-mem)
    clarifier/
      agent.py
      voi.py             # value-of-information thresholds
      questions.py       # templates
    discovery/
      agent.py
      sources/
        reddit.py
        blogs.py
        retailer.py      # mock adapters first
    normalizer/
      agent.py
      canon.py           # canonicalization, dedupe
    ranker/
      agent.py
      sentiment.py       # HF/heuristic switch; aspect sentiment
      proscons.py
    verifier/
      agent.py
      checks.py          # budget, OOS, duplicates, evidence
  tests/
    test_end_to_end.py
    test_ranker.py
    test_normalizer.py
  demo/
    demo_scenarios.md    # scripts to perform during judging

Environment & deps

Python 3.11+

requirements.txt (lean, hackathon-friendly):

uagents==0.12.0
pydantic==2.8.2
httpx==0.27.2
beautifulsoup4==4.12.3
rapidfuzz==3.9.6
numpy==2.1.1
scikit-learn==1.5.1
nltk==3.9.1


(If you add HF models later: transformers, torch, sentence-transformers.)

.env.example

ENV=dev
MAX_TOPK=3
MOCK_MODE=true

Task board (checklist)
Phase 0 — Bootstrap

 Create repo + src/ layout above

 Add pyproject.toml, requirements.txt, README.md

 Implement common/utils.py logger (request_id correlation)

 Implement common/bus.py (simple in-proc pub/sub with asyncio queues)

Phase 1 — Contracts & Tracing

 Define pydantic message contracts in common/messages.py (see below)

 Add trace fields: request_id, step, ts, source_agent

Phase 2 — Data & Heuristics (MVP)

 Load mocks/reviews_earbuds.json with ~5 products × 30 reviews each

 Implement aspects.py (keyword lists per category + simple regex)

 Implement scoring.py (rating, sentiment, recency, helpfulness terms)

Phase 3 — Execution Agents

 Discovery agent: return ProductCandidate[] from mocks

 Normalizer agent: canonicalize, dedupe (RapidFuzz), enrich signals

 Ranker agent: aspect sentiment (heuristic), pros/cons, composite score

 Wire Discovery→Normalizer→Ranker e2e (one run_pipeline() helper)

Phase 4 — Orchestration & Clarification

 Planner agent: parse NL → ShoppingBrief + plan steps

 Clarifier agent: VOI heuristic; ask ≤2 questions; cache answers

 Planner integrates Clarifier only when voi.trigger == True

Phase 5 — Verification & Adaptation

 Verifier agent: budget, OOS (mock), duplicates, evidence threshold

 Planner handles VerificationReport.passed == False → Replan:
- retry: re-discovery or next candidate
- or request user to relax constraints

Phase 6 — Demo & Output

 Return 3 product cards JSON with score, pros, cons, why

 demo/demo_scenarios.md with 3 scripted runs (incl. fail→replan)

 Pretty console renderer (optional) or lightweight FastAPI endpoint

Phase 7 — Fetch.ai / Agentverse polish

 Wrap each agent as a uagents agent with message handlers

 Implement Chat Protocol shim in Planner

 Register agents on Agentverse (README steps)

Message contracts (drop into src/common/messages.py)
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class Trace(BaseModel):
    request_id: str
    step: str
    source_agent: str
    ts: float

class ShoppingBrief(BaseModel):
    trace: Trace
    query: str
    category: Optional[str] = None
    use_case: Optional[str] = None
    constraints: Dict[str, float | int | str | bool] = {}
    weights: Dict[str, float] = {}
    success: Dict[str, int | bool] = {"k": 3, "diversity": True, "min_reviews": 50}

class ProductCandidate(BaseModel):
    trace: Trace
    name: str
    urls: Dict[str, str] = {}
    raw_reviews: List[Dict] = []  # {text, stars, date, helpful, verified}
    meta: Dict[str, float | int | str] = {}

class EnrichedProduct(BaseModel):
    trace: Trace
    canonical_id: str
    name: str
    price: Optional[float] = None
    stars: Optional[float] = None
    reviews_total: Optional[int] = None
    signals: Dict[str, float] = {}  # verified_pct, avg_helpful, recency_days_p50
    aspects: Dict[str, float] = {}  # aspect frequency (for weighting)

class RankedProduct(BaseModel):
    trace: Trace
    canonical_id: str
    name: str
    score: float
    pros: List[str]
    cons: List[str]
    why: Dict[str, float]  # rating/sentiment/recency/helpfulness weights
    price: Optional[float] = None
    stars: Optional[float] = None

class RankedList(BaseModel):
    trace: Trace
    items: List[RankedProduct]

class ClarificationRequest(BaseModel):
    trace: Trace
    missing: List[str]
    suggested_questions: List[str]
    context: Dict[str, str]

class ClarificationAnswer(BaseModel):
    trace: Trace
    answers: Dict[str, str | float | int | Dict[str, float]]

class VerificationReport(BaseModel):
    trace: Trace
    passed: bool
    checks: Dict[str, bool]
    notes: List[str] = []

🔀 Agent Flows (for Windsurf notes & team alignment)

Use these to guide implementation & testing. You can render the diagrams locally or just keep them as dev artifacts.

Global sequence (end-to-end)
sequenceDiagram
  participant User
  participant Planner
  participant Clarifier
  participant Discovery
  participant Normalizer
  participant Ranker
  participant Verifier

  User->>Planner: NL goal ("best earbuds under $150 for running")
  Planner->>Clarifier: ClarificationRequest? (only if VOI>τ)
  Clarifier-->>Planner: ClarificationAnswer (budget, priorities)
  Planner->>Discovery: ShoppingBrief
  Discovery-->>Planner: ProductCandidate[]
  Planner->>Normalizer: candidates
  Normalizer-->>Planner: EnrichedProduct[]
  Planner->>Ranker: enriched + weights
  Ranker-->>Planner: RankedList (top-k)
  Planner->>Verifier: top-3
  Verifier-->>Planner: VerificationReport (passed? fail reasons)
  alt passed
    Planner-->>User: 3 cards + score + pros/cons + why
  else fail
    Planner->>Discovery: Re-discover / next-best
    Planner->>Ranker: Re-score with adjustments
    Planner->>Verifier: Re-verify
    Verifier-->>Planner: passed
    Planner-->>User: final 3 cards
  end

Planner (Orchestrator) — state machine
stateDiagram-v2
  [*] --> PARSE
  PARSE --> CLARIFY : VOI > τ and missing slots
  PARSE --> DISCOVER : else
  CLARIFY --> DISCOVER : answers received or max Qs reached
  DISCOVER --> NORMALIZE : N >= min_candidates
  DISCOVER --> FAIL : timeout/no candidates
  NORMALIZE --> RANK
  RANK --> VERIFY
  VERIFY --> RETURN : passed
  VERIFY --> ADAPT : fail (budget/OOS/dup/evidence)
  ADAPT --> DISCOVER : need new candidates
  ADAPT --> RANK : reweight / swap candidate
  RETURN --> [*]
  FAIL --> [*]


Planner responsibilities

Build ShoppingBrief (category, use_case, constraints, weights).

Decide to call Clarifier (VOI).

Retry strategy: 1x rediscovery, 1x re-score before asking user to relax.

Clarifier — VOI policy
flowchart TD
A[Inputs: brief, candidate variance] --> B{Missing slots?}
B -- No --> D[Return empty]
B -- Yes --> C[Simulate two plausible answers → Δscore]
C --> E{Δscore > τ OR success not feasible?}
E -- No --> D
E -- Yes --> F[Ask top-1 (maybe top-2) question(s)]
F --> G[Return normalized answers]

Discovery — source selection & backoff
flowchart LR
Q[ShoppingBrief] --> S1[Search retailer (mock)]
Q --> S2[Search Reddit (mock)]
Q --> S3[Search blogs (mock)]
S1 --> M[Merge + Dedupe URLs]
S2 --> M
S3 --> M
M --> C{>= N distinct products?}
C -- Yes --> OUT[ProductCandidate[]]
C -- No --> BACKOFF[Expand query / use cached set] --> OUT

Normalizer — canonicalization & enrichment
flowchart LR
IN[ProductCandidate[]] --> Dedupe[RapidFuzz match names/SKUs]
Dedupe --> Canon[Canonical ID, brand, model]
Canon --> Enrich[price, stars, counts, verified_pct, avg_helpful, recency]
Enrich --> Aspects[keyword freq per aspect]
Aspects --> OUT[EnrichedProduct[]]

Ranker — aspect sentiment + pros/cons
flowchart LR
IN[EnrichedProduct[] + weights] --> Sent[Aspect sentiment (heuristic/HF)]
Sent --> Score[Composite score (rating/sent/recency/help)]
Score --> ProsCons[Clustered pros/cons]
ProsCons --> TopK[Select top-3 (diversity)]
TopK --> OUT[RankedList]

Verifier — constraint checks & adaptation hints
flowchart LR
IN[Top-3] --> Checks[Budget, OOS, Duplicates, Evidence]
Checks --> Pass{All pass?}
Pass -- Yes --> OUT[VerificationReport(passed=true)]
Pass -- No --> Hints[Which fail? Suggest next candidate / reweight] --> OUT[VerificationReport(passed=false)]

🧱 Minimal agent skeletons (drop into each agent.py)

Keep handlers tiny; forward only typed messages.

# src/planner/agent.py
from common.messages import *
from common.utils import logger
from .policy import build_brief, should_clarify, plan_steps

class PlannerAgent:
    async def handle_user_goal(self, text: str, request_id: str):
        trace = Trace(request_id=request_id, step="parse", source_agent="planner", ts=time.time())
        brief = build_brief(text, trace)

        if should_clarify(brief):
            clr_req = ClarificationRequest(
                trace=trace, missing=[...], suggested_questions=[...], context={"category": brief.category or ""}
            )
            answers = await self.clarifier.ask(clr_req)  # RPC or bus
            brief = self.apply_answers(brief, answers)

        candidates = await self.discovery.find(brief)
        enriched = await self.normalizer.enrich(candidates)
        ranked = await self.ranker.rank(enriched, brief.weights)
        report = await self.verifier.check(ranked, brief)

        if not report.passed:
            # simple adaptation loop
            ranked = await self.adapt_and_retry(brief, candidates, enriched, ranked, report)

        return self.to_cards(ranked)


(Repeat similarly small files for other agents—focus on I/O and single responsibility.)

🧪 Demo scenarios (put in demo/demo_scenarios.md)

Happy path:
Input: “Best wireless earbuds under $150 for running.”

Clarifier asks priorities (1 question).

Output: 3 cards + why.

Verification fail → Adapt:

Mock #2 OOS → Verifier fails → Planner swaps in #4 → returns new top-3.

Low evidence → Rediscovery:

Set min_reviews=200 → Verifier fails for #3 → Discovery expands sources → Ranker updates → pass.

✅ Implementation tips

Start mock-only; wire real scrapers last (or skip entirely for demo).

Keep agents stateless (Planner holds minimal session state).

Add request_id trace everywhere; judges love seeing reliable logs.

Expose a single CLI: python -m src.run "best earbuds under 150 for running" → prints 3 cards JSON.

If time permits: a tiny FastAPI endpoint returning the same JSON for a simple web UI.
# 🧠 Tech Stack Rationale — Why This Stack?

This document answers the question: *"Why did you choose X over Y for this project?"*
Every technology decision was deliberate. This is the reasoning behind each one.

---

## 1. 🐍 Python — Why not Node.js / Go?

**Chosen because:**
- Python is the **de-facto language of the AI/ML ecosystem**. LangChain, LangGraph, and every major LLM SDK (OpenAI, Groq, Anthropic) publish Python-first SDKs. The Go and Node.js equivalents are either incomplete, unofficial, or lag months behind in features.
- `asyncio` in Python 3.11+ is mature and handles concurrent I/O-bound work (LLM API calls) extremely efficiently without threads.
- This is an AI-native project. Using Python removes an entire category of integration friction.

**Why not Node.js:**
Node.js has `langchain.js`, but LangGraph's JavaScript SDK is significantly less mature than its Python counterpart. Native fan-out/fan-in `StateGraph` features are Python-first.

**Why not Go:**
Go has excellent concurrency primitives, but no first-class LLM orchestration ecosystem. You'd be building LangGraph from scratch.

---

## 2. ⚡ FastAPI — Why not Flask / Django?

**Chosen because:**
- **Async-native**: FastAPI is built on Starlette and supports `async def` handlers natively. Since the entire pipeline (fetching GitHub diffs, calling Groq, posting comments) is async I/O, using FastAPI means zero blocking and maximum concurrency under load.
- **Automatic docs**: FastAPI auto-generates OpenAPI (Swagger UI) docs at `/docs` with zero configuration — invaluable for testing the webhook endpoint during development.
- **Pydantic validation**: Built-in request validation catches malformed webhook payloads before they reach business logic.

**Why not Flask:**
Flask is WSGI-based and synchronous by default. Every LLM call (which takes 3–10 seconds) would block the entire worker thread. You'd need Gunicorn + multiple workers just to handle concurrent webhooks. Flask-async exists but it's a bolt-on, not a first-class design.

**Why not Django:**
Django is a full-stack framework built for database-backed web applications. This project has no ORM, no templates, no admin panel — Django would bring massive, irrelevant overhead. It's a bulldozer for a job that needs a scalpel.

---

## 3. 🔗 LangGraph — Why not raw asyncio / LangChain LCEL / CrewAI?

**Chosen because:**
- **Stateful graph execution**: LangGraph gives you a typed `StateGraph` where each node reads from and writes to a shared `ReviewState` TypedDict. This is the cleanest possible way to model a fan-out/fan-in multi-agent pipeline.
- **Automatic fan-in**: When multiple edges point to a single node (`security → synthesizer`, `performance → synthesizer`, `style → synthesizer`), LangGraph automatically waits for ALL predecessor nodes to complete before firing the synthesizer. This is not a feature you get for free with raw `asyncio`.
- **Production-ready patterns**: LangGraph is built for adding loops, conditional routing, and human-in-the-loop checkpoints in the future without a rewrite.

**Why not raw `asyncio.gather()`:**
`asyncio.gather` is excellent for simple parallel I/O, and the project even ships a native asyncio engine (`graph.py`) for comparison. However, for multi-agent pipelines, `asyncio` has no concept of shared typed state, no visual graph topology, and no built-in support for conditional branching or loops. It scales poorly as the graph grows.

**Why not LangChain LCEL (pipes `|`):**
LCEL is designed for single-chain, linear pipelines (prompt → LLM → parser). It does not natively model DAGs (Directed Acyclic Graphs) with fan-out/fan-in patterns. Forcing a parallel fan-out into LCEL requires hacky workarounds with `RunnableParallel` that obscure the architecture instead of clarifying it.

**Why not CrewAI:**
CrewAI is a higher-level abstraction that hides the graph entirely. It's excellent for quick prototyping, but it trades control for convenience. For this project, knowing *exactly* what each node does, how state flows, and being able to add fault isolation per-node required the lower-level control that LangGraph provides.

**Why not AutoGen (Microsoft):**
AutoGen's model is conversational agents talking to each other in a loop until they reach consensus. That's a powerful pattern for open-ended research tasks, but fundamentally wrong for this use case. Code review has a fixed, predictable structure: 3 parallel analyses → 1 synthesis. AutoGen's overhead (multi-turn back-and-forth) would be wasteful and slow.

---

## 4. 🦙 Groq + Llama 3.3 70B — Why not OpenAI GPT-4 / Anthropic Claude / local Ollama?

**Chosen because:**
- **Speed**: Groq's LPU (Language Processing Unit) inference is genuinely 10–20x faster than GPU-based cloud providers. For a PR review bot, latency matters — developers don't want to wait 90 seconds for a comment.
- **Free tier**: Groq offers a generous free tier, making this project runnable at zero cost for solo developers and demos.
- **Llama 3.3 70B quality**: Meta's Llama 3.3 70B is a state-of-the-art open-weight model that matches GPT-4-class performance on code reasoning benchmarks.

**Why not OpenAI GPT-4o:**
GPT-4o is excellent but expensive. Running 4 LLM calls (3 specialists + 1 synthesizer) per PR, at GPT-4o pricing, would cost ~$0.05–$0.15 per review. On an active repository with dozens of PRs per day, that adds up quickly. Groq + Llama 3.3 70B delivers comparable quality at ~10x lower cost.

**Why not Anthropic Claude:**
Claude is outstanding for long-context reasoning, but it's similarly expensive and slower than Groq for short, structured tasks like code review. Groq's raw speed is a hard-to-beat advantage for a latency-sensitive webhook handler.

**Why not local Ollama:**
Local inference via Ollama would make the project impossible to deploy as a server-side webhook receiver without access to expensive GPU hardware. It's great for laptop demos but not for a production bot that needs to be always-on and accessible via a public URL.

---

## 5. 🔐 HMAC SHA-256 Webhook Verification — Why not API keys / JWT / OAuth?

**Chosen because:**
- GitHub's webhook security model **specifically uses HMAC SHA-256 signatures**. When GitHub sends a webhook, it signs the raw request body with the shared `WEBHOOK_SECRET` using HMAC-SHA256 and places the result in the `X-Hub-Signature-256` header.
- Verifying this signature is the only way to cryptographically prove that a request genuinely came from GitHub and was not tampered with in transit. It protects the endpoint from being spammed by any malicious actor who discovers the public URL.
- This is the **industry standard** for webhook security. It's what Stripe, GitHub, Slack, and all major webhook providers use.

**Why not a shared API key in a header:**
A simple API key header is static and replayable. If it's intercepted once, an attacker can replay any crafted payload forever. HMAC signatures are computed over the *body* of each request, so every signature is unique and payload-bound.

**Why not JWT:**
JWTs are for authenticating *users* to *your* service. The webhook scenario is the reverse: *GitHub* needs to prove its identity to *your server*. HMAC is the correct, purpose-built tool for this.

---

## 6. 📦 `TypedDict` for State — Why not Pydantic / dataclasses / plain `dict`?

**Chosen because:**
- LangGraph's `StateGraph` requires the state to be a `TypedDict`. It inspects the type annotations to know which keys to merge when nodes return partial state updates.
- `TypedDict` is zero-overhead at runtime (it's just a `dict` with type hints), while Pydantic adds serialization/validation overhead that is unnecessary for in-memory graph state.
- It provides full IDE type-checking and autocomplete across all nodes without any runtime cost.

**Why not plain `dict`:**
A plain `dict` has no type annotations, meaning the IDE can't warn you if a node tries to read `state['perfomance_review']` (typo) instead of `state['performance_review']`. `TypedDict` catches these bugs at development time.

**Why not Pydantic `BaseModel`:**
Pydantic `BaseModel` instances are not plain dicts — LangGraph cannot directly use them as state without extra adapter code. `TypedDict` is the idiomatic, recommended state type in the LangGraph documentation.

---

## Summary Table

| Technology | Chosen For | Key Alternative Rejected | Reason Rejected |
|---|---|---|---|
| **Python** | Language | Node.js, Go | LangGraph/LangChain are Python-first |
| **FastAPI** | Web Framework | Flask, Django | Flask is sync-blocking; Django is over-engineered for this |
| **LangGraph** | Agent Orchestration | CrewAI, AutoGen, raw asyncio | Provides typed state, native fan-in, and future extensibility |
| **Groq + Llama 3.3** | LLM Inference | GPT-4o, Claude | 10–20x faster inference; free tier; comparable quality |
| **HMAC SHA-256** | Webhook Security | API keys, JWT | GitHub's native signing scheme; payload-bound; non-replayable |
| **TypedDict** | Graph State | Pydantic, plain dict | Zero-overhead; LangGraph-native; IDE type-safety |

---

*Every choice here was driven by the same three constraints: **speed**, **cost**, and **production correctness**.*

---
---
---
Here is a set of strong, technical AI Engineering mock interview questions based directly on your **AI Code Review Agent** project. I've included short, punchy answers that highlight your architectural decisions.

### 1. Architecture: Single vs. Multi-Agent
**Question:** *"I see you built a multi-agent system with three specialist agents and a synthesizer. Why did you choose this architecture over simply passing a single massive prompt to one LLM and asking it to review security, performance, and style all at once?"*

**Answer:** 
"Using a single prompt for everything often leads to 'attention dilution' or 'lazy generation' where the LLM focuses on one area (like style) and ignores the others (like security). By splitting the responsibilities into specialized agents, I force the LLM to focus purely on one domain per generation. The Synthesizer then reliably aggregates these focused findings. It costs a bit more in tokens, but the quality, depth, and reliability of the review are significantly higher."

### 2. Orchestration: LangGraph vs. Asyncio
**Question:** *"Your project supports both LangGraph and native Python `asyncio.gather` for parallel execution. What is the actual value of using LangGraph here? Why not just stick to native Python async?"*

**Answer:** 
"Native `asyncio.gather` is great for simple parallel I/O, but LangGraph provides a true state machine (`StateGraph`). While they do the exact same thing in my current fan-out/fan-in design, LangGraph makes it much easier to scale the system in the future. For example, if I wanted to add 'loops' (like having an agent revise its answer if the Synthesizer rejects it) or 'human-in-the-loop' approvals, LangGraph handles that state management natively, whereas native `asyncio` would become a messy web of `while` loops and complex state passing."

### 3. Reliability: Graceful Degradation (Fault Tolerance)
**Question:** *"LLM APIs are notorious for rate limits and timeouts. In your parallel fan-out/fan-in graph, what happens if the Security agent succeeds, but the Performance agent hits an API timeout?"*

**Answer:** 
"I implemented graceful degradation with per-node fault isolation. Instead of letting an exception crash the entire `StateGraph` or `asyncio.gather` call (which would bypass the Synthesizer entirely and fail the review), each specialist node wraps its LLM call in a `try-except` block. If the Performance agent fails, it catches the error and returns a predefined fallback state (e.g., 'Performance review unavailable'). The graph's Fan-In requirement is still met, the Synthesizer runs successfully, and the user gets a partial review instead of a complete failure."

### 4. Prompt Engineering: Hallucination Prevention
**Question:** *"AI code reviewers often hallucinate bugs or critique code that the developer didn't even touch. How did you design your prompts to prevent this?"*

**Answer:** 
"I implemented strict '*Evidence Rules*' in a shared prompt template injected into every specialist. First, I explicitly instruct the LLM to only look at added lines (lines starting with `+` but not `+++`). Second, I require the LLM to output its findings in a strict schema (Severity, Confidence, Line Number, and Suggested Fix). By forcing the LLM to provide the exact line number and a concrete code snippet fix, it naturally grounds the model and drastically reduces hallucinations."

### 5. System Design: Context Limits
**Question:** *"What happens if a developer opens a massive PR that changes 50 files, and the diff exceeds the context window of Llama 3 (or Groq's token limits)?"*

**Answer:** 
"Currently, the system would fail or truncate the prompt. If I were to scale this for enterprise, I would implement a chunking strategy. I would parse the diff and split it by file or logical chunks. I could run the specialist agents on a per-file basis concurrently, and then use a hierarchical Synthesizer: first summarizing issues per-file, and then doing a final global synthesis to post to GitHub."


### 6. Code Context: Diffs vs. Full Codebase
**Question:** *"In your system, are you sending the entire codebase to the LLMs, or just the git diffs? If you only send the diffs, how do the agents understand the full context of the code? Aren't they missing the big picture?"*

**Answer:** 
"Currently, the system only sends the **git diffs**. Sending the entire codebase for every PR is too slow, incredibly expensive, and usually blows past the LLM's context window. 

You are right that sending only the diff limits context—the LLM might not know what a specific imported function does. To handle this right now, I implemented strict **'Evidence Rules'** in the system prompt. The LLM is explicitly instructed to only critique what is directly visible in the added lines and to state 'Cannot determine from the provided diff' if it lacks context, rather than hallucinating.

*If they ask how you would fix the context issue in the future, add:*
"To solve this properly in a V2, I would implement **RAG (Retrieval-Augmented Generation)**. I would chunk and embed the repository, and when a PR comes in, I would retrieve the definitions of the functions or classes being modified and inject that specific context alongside the diff. Another option is using an AST (Abstract Syntax Tree) parser to pull in the exact file dependencies."
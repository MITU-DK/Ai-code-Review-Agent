# 🤖 AI Code Review Agent

An **enterprise-grade, multi-agent AI system** that automatically reviews GitHub Pull Requests the moment they are opened. It uses a LangGraph-powered pipeline of specialist AI agents running in **parallel** to provide fast, structured, and professional code reviews directly as GitHub PR comments.

---

## ✨ Features

- **Automated PR Reviews** — Triggers automatically via GitHub Webhooks when a PR is opened or updated.
- **Multi-Agent Architecture** — 3 specialist AI agents (Security, Performance, Style) run in parallel for superior analysis quality.
- **LangGraph Fan-Out / Fan-In** — True parallel execution using LangGraph's native `StateGraph`.
- **Structured Feedback** — Every finding includes Severity, Confidence, Line Number, and a concrete code fix.
- **Graceful Degradation** — If any specialist agent fails (e.g. API timeout, rate limit), the pipeline continues and the Synthesizer produces a review using the available reports. No single agent failure can crash the entire review.
- **Asynchronous Webhooks** — Uses FastAPI `BackgroundTasks` to instantly respond to GitHub, preventing webhook timeout failures.
- **Secure Webhook Handling** — All incoming webhooks are verified using `X-Hub-Signature-256` HMAC authentication.
- **Modular Codebase** — Clean, professional package structure. Every concern is separated into its own file.

---

## 🏗️ Architecture

```
                     ┌──> Security Agent ─────────────────────┐
GitHub PR ──> POST /webhook ──> Performance Agent ───> Synthesizer ──> GitHub PR Comment
                     └──> Style Agent ────────────────────────┘
```

### Agent Responsibilities

| Agent | Finds |
|---|---|
| 🛡️ **Security & Correctness** | Hardcoded secrets, SQL injection, XSS, race conditions, logic errors |
| ⚡ **Performance** | N+1 queries, blocking I/O in async context, memory issues |
| 🧹 **Code Quality & Style** | SRP violations, poor naming, DRY violations, swallowed exceptions |
| 🧠 **Synthesizer** | Merges all 3 reports, removes duplicates, formats the final GitHub comment |

### Graceful Degradation

Each specialist agent is independently wrapped in fault isolation. If an agent fails for any reason (API timeout, rate limit, network error), it returns a clear fallback message instead of crashing the pipeline:

```
⚠️ Performance review unavailable — agent encountered an error.
```

The Synthesizer **always runs** with whatever reports are available, and the failure is logged for debugging. This means:

| Scenario | Behaviour |
|---|---|
| All 3 agents succeed | Full review posted to PR ✅ |
| 1 agent fails | Review posted with 2 sections + fallback notice for the failed one ✅ |
| 2 agents fail | Review posted with 1 section + 2 fallback notices ✅ |
| All 3 agents fail | Review posted with 3 fallback notices + Overall Assessment ✅ |

---

## 🗂️ Project Structure

```
Ai-Code-Review-Agent/
├── src/
│   ├── main.py               # FastAPI app entry point & startup config
│   ├── config.py             # Single source of truth for all env variables
│   ├── security.py           # HMAC webhook signature verification
│   ├── github_client.py      # GitHub API: fetch diffs, post comments
│   ├── prompts.py            # All 4 LLM agent prompts (modular)
│   ├── agent/
│   │   ├── __init__.py       # 🔁 Engine switch: LangGraph vs asyncio
│   │   ├── state.py          # ReviewState TypedDict (shared graph state)
│   │   ├── llm.py            # Groq LLM client + call_llm() wrapper
│   │   ├── nodes.py          # Specialist agent nodes (asyncio engine) with per-node fault isolation
│   │   ├── graph.py          # Engine 1: asyncio.gather() parallel execution
│   │   └── graph_langgraph.py # Engine 2: True LangGraph fan-out/fan-in with per-node fault isolation
│   └── routes/
│       ├── webhook.py        # POST /webhook — main PR review trigger
│       └── health.py         # GET / — health check endpoint
├── .env.example              # Template for required environment variables
├── .gitignore                # .env is excluded — secrets are never committed
└── requirements.txt          # Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- A GitHub account with a repository you want to review
- A free [Groq API Key](https://console.groq.com)
- [ngrok](https://ngrok.com) (for local development)

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/Ai-Code-Review-Agent.git
cd Ai-Code-Review-Agent
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
```
Now open `.env` and fill in your values:

```env
GITHUB_TOKEN=your_github_personal_access_token
WEBHOOK_SECRET=your_webhook_secret_string
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

### 5. Start the Server
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Expose It with ngrok
```bash
ngrok http 8000
```
Copy the `https://...ngrok-free.app` URL from the terminal.

### 7. Configure the GitHub Webhook
1. Go to your GitHub Repository → **Settings → Webhooks → Add webhook**.
2. **Payload URL:** `https://your-ngrok-url.ngrok-free.app/webhook`
3. **Content type:** `application/json`
4. **Secret:** Same value as `WEBHOOK_SECRET` in your `.env`
5. **Events:** Select **"Pull requests"** only.
6. Click **Add webhook**.

Now open a Pull Request in your repository and watch the AI review appear automatically! 🎉

---

## ⚙️ Switching Execution Engines

Open [`src/agent/__init__.py`](src/agent/__init__.py) and change one line:

```python
# True LangGraph parallel execution (recommended for resume / production)
USE_LANGGRAPH = True

# Native Python asyncio.gather() (faster startup, simpler debugging)
USE_LANGGRAPH = False
```

Both engines produce **identical output** and both support full graceful degradation. The difference is purely how they orchestrate the parallel execution internally.

---

## 📋 Example Review Output

```markdown
## 🤖 AI Code Review

> Multi-agent review powered by llama-3.3-70b-versatile via Groq.
> 3 specialist nodes ran in parallel.

---
## 🛡️ Security & Correctness
- **Severity**: CRITICAL
- **Confidence**: HIGH
- **File**: app/auth.py
- **Line**: +4

**Problem**: Hardcoded API key exposed in source code.
**Why it matters**: Credentials committed to git history can never be truly deleted.
**Suggested Fix**:
  API_KEY = os.environ.get("API_KEY")

---
## ⚡ Performance
⚠️ Performance review unavailable — agent encountered an error.

---
## 🧹 Code Quality & Maintainability
No issues found ✅

## Overall Assessment
REQUEST CHANGES ❌ — Critical security issue found.
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **FastAPI** | High-performance async web framework |
| **LangGraph** | Multi-agent graph orchestration with fan-out/fan-in |
| **LangChain + Groq** | LLM inference (Llama 3.3 70B) |
| **PyGithub** | GitHub API client |
| **Python asyncio** | Concurrent parallel execution |
| **HMAC SHA-256** | Webhook security signature verification |

---

## 🔮 Future Enhancements

- [ ] **Inline PR Comments** — Attach findings to specific line numbers in the diff view
- [ ] **One-Click Auto-Fix** — Post GitHub "Suggested Changes" that developers can apply with one click
- [ ] **RAG Context** — Index the full codebase in a vector DB so agents understand custom functions
- [ ] **Interactive Chatbot** — Reply to the AI's review comments to get follow-up answers
- [ ] **GitHub App** — Convert to a public GitHub App so anyone can install with one click
- [ ] **Background Queue** — Add Celery + Redis for enterprise-scale webhook processing

---

## ⚠️ Known Limitations

These are honest, known constraints of the current V1 implementation. Each one has a clear path to resolution in a future version.

### 1. Diff-Only Context (No Full Codebase Awareness)
The agents only receive the **git diff**, not the full codebase. This means they cannot see the definition of a function being called, the full class a method belongs to, or any imported module's behaviour.

**Impact:** The agents may flag issues they lack full context to verify, or miss issues that only appear when combining the new code with existing code.

**V2 Fix:** Implement RAG (Retrieval-Augmented Generation) — embed the repository and retrieve relevant file chunks alongside the diff at review time.

---

### 2. No Token / Context Window Guard
There is no check on the size of the diff before sending it to Groq. A very large PR (e.g. 50+ files changed) can exceed the model's context window, causing the API to return a truncated or errored response.

**Impact:** Large PRs may receive an incomplete or failed review with no clear user-facing error.

**V2 Fix:** Parse the diff, measure token count using `tiktoken`, and split oversized diffs into per-file chunks. Run agents per-chunk, then hierarchically synthesize.

---

### 3. No Retry / Rate-Limit Back-Off
The `call_llm()` function makes a single attempt to the Groq API with no retry logic. If the API returns a `429 Too Many Requests` or a transient `500` error, the node immediately falls back to its graceful degradation message.

**Impact:** Transient errors that would succeed on a retry result in a section being marked as unavailable when it didn't need to be.

**V2 Fix:** Wrap `call_llm()` with exponential back-off retry logic using `tenacity`.

### 4. No Persistent State or Audit Log
Reviews are not stored anywhere. Once a review is posted to GitHub, there is no local record of what was reviewed, what the agent found, or how long it took.

**Impact:** Impossible to debug past reviews, measure agent accuracy over time, or build analytics on common issue types.

**V2 Fix:** Persist each review run to a database (e.g. SQLite for local, PostgreSQL for production) with the PR metadata, agent outputs, and latency metrics.

---

### 5. In-Process Background Tasks (No Job Persistence)
Webhook processing is offloaded using FastAPI's `BackgroundTasks`, which runs jobs **inside the same server process**. This is significantly better than blocking the HTTP response, but it is not a true durable queue.

**Impact:**
- If the server crashes or restarts mid-review, the in-flight job is **silently lost** with no retry.
- Under high traffic (many PRs at once), all background tasks compete for the same process memory, which can degrade performance.
- There is no visibility into queued jobs — you cannot see their status, failures, or retry counts.

**V2 Fix:** Replace `BackgroundTasks` with **Celery + Redis**. Tasks are persisted to Redis before execution, survive server crashes, support automatic retries, and can be monitored via a dashboard (Flower).

---


## 🔐 Security

- The `.env` file is listed in `.gitignore` and is **never committed to Git**.
- All webhook payloads are authenticated via **HMAC SHA-256 signature verification** before any processing occurs.
- All API keys are loaded exclusively from environment variables via `src/config.py`. No keys are hardcoded anywhere in the source code.

---

## 📄 License

MIT License — feel free to use, modify, and distribute this project.

---

*Built with ❤️ and LangGraph*

"""
graph_langgraph.py — LANGGRAPH-NATIVE parallel multi-agent pipeline.

This is the LangGraph version of the review pipeline.
It uses LangGraph's native fan-out/fan-in to run 3 specialist
agents IN PARALLEL, then feeds all 3 into the Synthesizer.

Graph topology:
                    ──> security_agent ────>
    START ─────>    ──> performance_agent ───>  synthesizer ───> END
                    ──> style_agent ──────────>

Key LangGraph concepts demonstrated here:
  - StateGraph   -> the DAG that holds all nodes and edges
  - ReviewState  -> the Shared typed Dict passed between nodes
  - Fan-out      -> START fires 3 nodes simultaneously
  - Fan-in       -> LangGraph waits for all 3 before running synthesizer
  - Async nodes  -> each node is a proper async coroutine

This is the architecture you'd put on a resume to showcase LangGraph.
"""

import asyncio
import logging

from langgraph.graph import END, START, StateGraph

from src.agent.llm import call_llm
from src.agent.state import ReviewState
from src.config import GROQ_MODEL
from src.prompts import (
    PERFORMANCE_AGENT_PROMPT,
    SECURITY_AGENT_PROMPT,
    STYLE_AGENT_PROMPT,
    SYNTHESIZER_AGENT_PROMPT,
)

logger = logging.getLogger(__name__)


#  Async Node Functions — LangGraph requires async nodes for parallel execution

async def security_node(state: ReviewState) -> dict:
    """Security & Correctness specialist — runs as a LangGraph async node."""
    logger.info("🛡️  [LangGraph Security Node] Running...")
    try:
        result = await asyncio.to_thread(
            call_llm,
            SECURITY_AGENT_PROMPT,
            f"Review this diff for Security and Correctness issues:\n\n{state['diff_text']}",
        )
        logger.info("🛡️  [LangGraph Security Node] Done.")
    except Exception as e:
        logger.error(f"❌ [LangGraph Security Node] Failed: {type(e).__name__}: {e}")
        result = "⚠️ Security & Correctness review unavailable — agent encountered an error."
    return {"security_review": result}


async def performance_node(state: ReviewState) -> dict:
    """Performance specialist — runs as a LangGraph async node."""
    logger.info("⚡ [LangGraph Performance Node] Running...")
    try:
        result = await asyncio.to_thread(
            call_llm,
            PERFORMANCE_AGENT_PROMPT,
            f"Review this diff for Performance issues:\n\n{state['diff_text']}",
        )
        logger.info("⚡ [LangGraph Performance Node] Done.")
    except Exception as e:
        logger.error(f"❌ [LangGraph Performance Node] Failed: {type(e).__name__}: {e}")
        result = "⚠️ Performance review unavailable — agent encountered an error."
    return {"performance_review": result}


async def style_node(state: ReviewState) -> dict:
    """Code Quality & Style specialist — runs as a LangGraph async node."""
    logger.info("🧹 [LangGraph Style Node] Running...")
    try:
        result = await asyncio.to_thread(
            call_llm,
            STYLE_AGENT_PROMPT,
            f"Review this diff for Code Quality and Style issues:\n\n{state['diff_text']}",
        )
        logger.info("🧹 [LangGraph Style Node] Done.")
    except Exception as e:
        logger.error(f"❌ [LangGraph Style Node] Failed: {type(e).__name__}: {e}")
        result = "⚠️ Code Quality & Style review unavailable — agent encountered an error."
    return {"style_review": result}


async def synthesizer_node(state: ReviewState) -> dict:
    """
    Synthesizer — LangGraph will only execute this node AFTER all three
    specialist nodes above have completed (automatic fan-in).
    """
    logger.info("🧠 [LangGraph Synthesizer Node] Merging reports...")
    combined_input = (
        f"## Security & Correctness Report\n{state['security_review']}\n\n"
        f"## Performance Report\n{state['performance_review']}\n\n"
        f"## Code Quality & Style Report\n{state['style_review']}"
    )
    result = await asyncio.to_thread(
        call_llm,
        SYNTHESIZER_AGENT_PROMPT,
        combined_input,
    )
    logger.info("🧠 [LangGraph Synthesizer Node] Done.")
    return {"final_review": result}


#  Graph Definition — this is the pure LangGraph architecture

def build_langgraph() -> StateGraph:
    """
    Builds and compiles the true LangGraph parallel pipeline.

    Fan-out: START simultaneously fires security, performance, and style nodes.
    Fan-in:  LangGraph automatically waits for all 3 to finish before running
             the synthesizer node.
    """
    graph = StateGraph(ReviewState)

    # Register all nodes
    graph.add_node("security", security_node)
    graph.add_node("performance", performance_node)
    graph.add_node("style", style_node)
    graph.add_node("synthesizer", synthesizer_node)

    # Fan-out: START → 3 parallel specialist branches
    graph.add_edge(START, "security")
    graph.add_edge(START, "performance")
    graph.add_edge(START, "style")

    # Fan-in: all 3 specialists must complete before synthesizer fires
    graph.add_edge("security", "synthesizer")
    graph.add_edge("performance", "synthesizer")
    graph.add_edge("style", "synthesizer")

    # Synthesizer → done
    graph.add_edge("synthesizer", END)

    return graph.compile()


#  Public entry point — mirrors the interface of graph.py exactly

_compiled_graph = build_langgraph()


async def analyze_code(diff_text: str) -> str:
    """
    Runs the LangGraph-native parallel review pipeline on a PR diff.

    LangGraph manages the fan-out and fan-in automatically.
    No manual asyncio.gather() needed.
    """
    if not diff_text.strip():
        logger.warning("⚠️  analyze_code() called with empty diff. Skipping.")
        return "⚠️ No code changes were provided for review."

    logger.info(f"🤖 [LangGraph] Starting multi-agent review ({GROQ_MODEL})...")

    try:
        initial_state: ReviewState = {
            "diff_text": diff_text,
            "security_review": "",
            "performance_review": "",
            "style_review": "",
            "final_review": "",
        }

        # LangGraph drives the entire parallel execution from here
        final_state = await _compiled_graph.ainvoke(initial_state)
        review_text = final_state["final_review"]

        logger.info(
            f"✅ [LangGraph] Review complete. ({len(review_text)} characters)"
        )

        formatted_review = (
            f"## 🤖 AI Code Review\n\n"
            f"> *Multi-agent review powered by `{GROQ_MODEL}` via Groq. "
            f"Built with LangGraph — 3 specialist nodes ran in parallel.*\n\n"
            f"{review_text}\n\n"
            f"---\n"
            f"*This review was generated automatically. Always apply human judgement.*\n"
            f"*Peace Out Man 😎*"
        )
        return formatted_review

    except RuntimeError as e:
        logger.error(f"❌ Configuration error: {e}")
        return f"❌ **AI Review Failed:** Configuration error — {e}"
    except Exception as e:
        logger.error(f"❌ LangGraph pipeline failed: {e}")
        return (
            f"❌ **AI Review Failed:** `{type(e).__name__}: {e}`\n\n"
            f"Please review this PR manually."
        )

"""
graph.py — asyncio-based parallel multi-agent pipeline.

Orchestrates the 3 specialist agents concurrently using Python's native
asyncio.gather(), then feeds all results into the Synthesizer agent.

Use this engine when you want maximum simplicity and speed without
the overhead of the LangGraph runtime.
"""
import asyncio
import logging

from src.config import GROQ_MODEL
from src.agent.state import ReviewState
from src.agent.nodes import (
    run_security_agent,
    run_performance_agent,
    run_style_agent,
    run_synthesizer_agent,
)

logger = logging.getLogger(__name__)

async def analyze_code(diff_text: str) -> str:
    """
    Runs the multi-agent review pipeline on a PR diff.
    """
    if not diff_text.strip():
        logger.warning("⚠️  analyze_code() called with empty diff. Skipping.")
        return "⚠️ No code changes were provided for review."

    logger.info(f"🤖 Starting multi-agent review ({GROQ_MODEL})...")

    try:
        # Step 1: Run all 3 specialist agents concurrently
        security_task = asyncio.to_thread(
            run_security_agent, {"diff_text": diff_text}
        )
        performance_task = asyncio.to_thread(
            run_performance_agent, {"diff_text": diff_text}
        )
        style_task = asyncio.to_thread(
            run_style_agent, {"diff_text": diff_text}
        )

        security_result, performance_result, style_result = await asyncio.gather(
            security_task, performance_task, style_task
        )

        logger.info("✅ All 3 specialist agents completed. Running synthesizer...")

        # Step 2: Feed all reports into the Synthesizer
        synthesizer_input: ReviewState = {
            "diff_text": diff_text,
            "security_review": security_result["security_review"],
            "performance_review": performance_result["performance_review"],
            "style_review": style_result["style_review"],
            "final_review": "",
        }

        synthesizer_output = await asyncio.to_thread(
            run_synthesizer_agent, synthesizer_input
        )
        review_text = synthesizer_output["final_review"]

        logger.info(
            f"✅ Multi-agent review complete. "
            f"({len(review_text)} characters)"
        )

        # Step 3: Wrap in a header for the GitHub comment
        formatted_review = (
            f"## 🤖 AI Code Review\n\n"
            f"> *Multi-agent review by [AI Code Review Agent](https://github.com) "
            f"powered by `{GROQ_MODEL}` via Groq. "
            f"3 specialist agents ran in parallel.*\n\n"
            f"{review_text}\n\n"
            f"---\n"
            f"*This review was generated automatically. Always apply human judgement.*\n"
            f"*Peace Out Man 😎*"
        )

        return formatted_review

    except RuntimeError as e:
        logger.error(f"❌ Configuration error in analyze_code: {e}")
        return f"❌ **AI Review Failed:** Configuration error — {e}"
    except Exception as e:
        logger.error(f"❌ Multi-agent pipeline failed: {e}")
        return (
            f"❌ **AI Review Failed:** The agent pipeline encountered an error: "
            f"`{type(e).__name__}: {e}`\n\n"
            f"Please review this PR manually."
        )

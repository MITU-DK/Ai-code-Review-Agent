"""
nodes.py — The individual specialist agents for the review pipeline.
"""
import logging
from src.agent.state import ReviewState
from src.agent.llm import call_llm
from src.prompts import (
    PERFORMANCE_AGENT_PROMPT,
    SECURITY_AGENT_PROMPT,
    STYLE_AGENT_PROMPT,
    SYNTHESIZER_AGENT_PROMPT,
)

logger = logging.getLogger(__name__)

def run_security_agent(state: ReviewState) -> dict:
    """Security & Correctness specialist node."""
    logger.info("🛡️  [Security Agent] Running...")
    try:
        result = call_llm(
            system_prompt=SECURITY_AGENT_PROMPT,
            user_message=f"Review this diff for Security and Correctness issues:\n\n{state['diff_text']}",
        )
        logger.info("🛡️  [Security Agent] Done.")
    except Exception as e:
        logger.error(f"❌ [Security Agent] Failed: {type(e).__name__}: {e}")
        result = "⚠️ Security & Correctness review unavailable — agent encountered an error."
    return {"security_review": result}

def run_performance_agent(state: ReviewState) -> dict:
    """Performance specialist node."""
    logger.info("⚡ [Performance Agent] Running...")
    try:
        result = call_llm(
            system_prompt=PERFORMANCE_AGENT_PROMPT,
            user_message=f"Review this diff for Performance issues:\n\n{state['diff_text']}",
        )
        logger.info("⚡ [Performance Agent] Done.")
    except Exception as e:
        logger.error(f"❌ [Performance Agent] Failed: {type(e).__name__}: {e}")
        result = "⚠️ Performance review unavailable — agent encountered an error."
    return {"performance_review": result}

def run_style_agent(state: ReviewState) -> dict:
    """Code Quality & Style specialist node."""
    logger.info("🧹 [Style Agent] Running...")
    try:
        result = call_llm(
            system_prompt=STYLE_AGENT_PROMPT,
            user_message=f"Review this diff for Code Quality and Style issues:\n\n{state['diff_text']}",
        )
        logger.info("🧹 [Style Agent] Done.")
    except Exception as e:
        logger.error(f"❌ [Style Agent] Failed: {type(e).__name__}: {e}")
        result = "⚠️ Code Quality & Style review unavailable — agent encountered an error."
    return {"style_review": result}

def run_synthesizer_agent(state: ReviewState) -> dict:
    """Synthesizer node — merges all 3 specialist reports into one final review."""
    logger.info("🧠 [Synthesizer Agent] Merging reports...")
    
    combined_input = (
        f"## Security & Correctness Report\n{state['security_review']}\n\n"
        f"## Performance Report\n{state['performance_review']}\n\n"
        f"## Code Quality & Style Report\n{state['style_review']}"
    )

    result = call_llm(
        system_prompt=SYNTHESIZER_AGENT_PROMPT,
        user_message=combined_input,
    )
    logger.info("🧠 [Synthesizer Agent] Done.")
    return {"final_review": result}

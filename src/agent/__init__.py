"""
agent package — Entry point for the AI Code Reviewer.

HOW TO SWITCH ENGINES:
  Set USE_LANGGRAPH = True  → Uses LangGraph's native parallel fan-out (resume-worthy)
  Set USE_LANGGRAPH = False → Uses Python asyncio.gather (faster, simpler)

Both engines produce identical output. The only difference is how they
orchestrate the parallel execution internally.
"""

# ── Switch between the two engines here 
USE_LANGGRAPH = True

if USE_LANGGRAPH:
    from src.agent.graph_langgraph import analyze_code  # noqa: F401
else:
    from src.agent.graph import analyze_code            # noqa: F401

__all__ = ["analyze_code"]

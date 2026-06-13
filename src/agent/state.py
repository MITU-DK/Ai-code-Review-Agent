"""
state.py — Defines the shared state for the LangGraph pipeline.
"""
from typing import TypedDict

class ReviewState(TypedDict):
    diff_text: str           # Input: the raw git diff
    security_review: str     # Output of Security & Correctness Agent
    performance_review: str  # Output of Performance Agent
    style_review: str        # Output of Style Agent
    final_review: str        # Output of Synthesizer Agent

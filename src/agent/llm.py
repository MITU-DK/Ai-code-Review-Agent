"""
llm.py — LLM client initialization and unified call logic.
"""
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from src.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

def get_llm() -> ChatGroq:
    """
    Returns an initialized Groq LLM client.
    Raises RuntimeError if GROQ_API_KEY is not configured.
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Cannot connect to Groq API. "
            "Please add it to your .env file."
        )
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0.2,  #more temperature make llm less deteministic
        max_tokens=2048,
    )

def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Makes a synchronous LLM call with a given system and user message.
    Returns the response content as a string.
    """
    llm = get_llm()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    
    response = llm.invoke(messages)
    return response.content

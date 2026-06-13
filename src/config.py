"""
config.py — Central configuration module.

All environment variables are loaded and validated here.
Every other module imports from here — never from os.getenv() directly.
This ensures a single source of truth for all settings.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# GitHub 
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")

# Groq / LLM 
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# App 
APP_TITLE: str = "AI Code Review Agent"
APP_DESCRIPTION: str = ("Automatically reviews GitHub Pull Requests using multi-agent LLM analysis.")
APP_VERSION: str = "1.0.0"


# Startup validation 
def validate_config() -> None:
    """
    Warns at startup if critical environment variables are missing.
    Called once when the FastAPI app starts up.
    """
    missing = []

    if not WEBHOOK_SECRET:
        missing.append("WEBHOOK_SECRET")
        logger.warning(
            "⚠️  WEBHOOK_SECRET is not set — signature verification is DISABLED. "
            "This is UNSAFE for production!"
        )
    if not GITHUB_TOKEN:
        missing.append("GITHUB_TOKEN")
        logger.warning("⚠️  GITHUB_TOKEN is not set — GitHub API calls will fail.")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
        logger.warning("⚠️  GROQ_API_KEY is not set — AI agent will not work.")

    if missing:
        logger.warning(
            f"📋 Missing environment variables: {', '.join(missing)}. "
            "Copy .env.example → .env and fill in the values."
        )
    else:
        logger.info("✅ All environment variables loaded successfully.")

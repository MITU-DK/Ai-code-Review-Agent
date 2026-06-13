"""
main.py — Application Entry Point.

This file does ONE thing only: create the FastAPI app, register
routers, configure logging, and run the server.

All business logic lives in dedicated modules:
  - config.py    → Environment variables & settings
  - security.py  → Webhook signature verification
  - routes/
      health.py  → GET /
      webhook.py → POST /webhook
"""

import logging

import uvicorn
from fastapi import FastAPI

from src.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION, validate_config
from src.routes import health, webhook

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
)

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(webhook.router)


# ── Startup event ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    """Runs once when the server starts — validates config and logs status."""
    validate_config()


# ── Dev server entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

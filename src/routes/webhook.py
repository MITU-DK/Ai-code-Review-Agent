"""
routes/webhook.py — GitHub Webhook Handler Route.

Responsibility: Receive, validate, and dispatch GitHub PR webhook events.

This module only handles HTTP-level concerns:
  - Reading the raw body
  - Calling security.verify_github_signature()
  - Parsing the JSON payload
  - Filtering events by type and action
  - Extracting PR metadata
  - Delegating to the AI agent (Phase 3+)

It does NOT contain business logic (security, AI analysis, GitHub API calls).
Those live in their own dedicated modules.
"""

import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.agent import analyze_code
from src.github_client import get_pr_diff, post_pr_comment
from src.security import verify_github_signature

logger = logging.getLogger(__name__)

router = APIRouter()

# Only these PR actions trigger a code review
PR_ACTIONS_TO_REVIEW = {"opened", "synchronize"}


@router.post(
    "/webhook",
    summary="GitHub Webhook Receiver",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Webhook"],
)
async def handle_webhook(
    request: Request,
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),  #getting signature 
) -> JSONResponse:
    """
    Receives and processes GitHub webhook events.

    Security:
        Validates the HMAC-SHA256 signature on every request.
        Returns 403 Forbidden if the signature does not match.

    Event Filtering:
        - Ignores all events except 'pull_request'.
        - Within 'pull_request' events, only processes 'opened' and 'synchronize'.

    Returns:
        202 Accepted  → Event received (and processed or intentionally ignored).
        400 Bad Request → Invalid JSON body.
        403 Forbidden → Signature verification failed.
    """
    # Step 1: Read raw body BEFORE any parsing (needed for signature check)
    payload_body = await request.body()

    # Step 2: Verify GitHub signature
    if not verify_github_signature(payload_body, x_hub_signature_256):
        logger.warning("🚨 Webhook rejected — invalid signature.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature. Request rejected.",
        )

    logger.info("✅ Webhook signature verified.")

    # Step 3: Parse JSON payload
    try:
        payload: dict = json.loads(payload_body)
    except json.JSONDecodeError:
        logger.error("❌ Failed to parse webhook payload as JSON.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    # Step 4: Filter — only handle 'pull_request' events
    logger.info(f"📨 Received GitHub event: '{x_github_event}'")

    if x_github_event != "pull_request":
        logger.info(f"⏭️  Ignoring non-PR event: '{x_github_event}'")
        return JSONResponse(
            content={"status": "ignored", "reason": f"Event '{x_github_event}' is not a pull_request."},
        )

    # Step 5: Filter — only review 'opened' and 'synchronize' actions
    action: str = payload.get("action", "")

    if action not in PR_ACTIONS_TO_REVIEW:
        logger.info(f"⏭️  Ignoring PR action: '{action}'")
        return JSONResponse(
            content={"status": "ignored", "reason": f"PR action '{action}' does not trigger a review."},
        )

    # Step 6: Extract PR metadata
    pull_request = payload.get("pull_request", {})
    pr_number: int = pull_request.get("number")
    pr_title: str = pull_request.get("title", "N/A")
    pr_author: str = pull_request.get("user", {}).get("login", "N/A")
    repo_full_name: str = payload.get("repository", {}).get("full_name", "N/A")

    logger.info("─" * 55)
    logger.info("🔔 NEW PR REVIEW TRIGGERED!")
    logger.info(f"   Repository : {repo_full_name}")
    logger.info(f"   PR Number  : #{pr_number}")
    logger.info(f"   PR Title   : {pr_title}")
    logger.info(f"   Author     : @{pr_author}")
    logger.info(f"   Action     : {action}")
    logger.info("─" * 55)

    # Step 7 (Phase 2): Fetch the PR diff from GitHub
    diff = await get_pr_diff(repo_full_name, pr_number)

    if not diff:
        logger.warning(f"⚠️  No diff found for PR #{pr_number}. Skipping review.")
        return JSONResponse(
            content={"status": "skipped", "reason": "No code changes found in this PR."},
        )

    logger.info(f"📄 Fetched diff for PR #{pr_number} ({len(diff)} characters)")

    # Step 8 (Phase 3): Run the AI agent to analyze the code diff
    logger.info(f"🤖 Running AI agent on PR #{pr_number}...")
    review = await analyze_code(diff)

    # Step 9 (Phase 2): Post the AI review comment back to the PR
    await post_pr_comment(repo_full_name, pr_number, review)

    logger.info(f"✅ Review comment posted on PR #{pr_number}")

    return JSONResponse(
        content={
            "status": "reviewed",
            "message": f"PR #{pr_number} in '{repo_full_name}' reviewed and commented.",
            "pr_title": pr_title,
            "author": pr_author,
        },
    )

"""
security.py — GitHub Webhook Signature Verification.

Isolates all security logic in one place.
Any module that needs to verify a webhook signature imports from here.

Why HMAC-SHA256?
    GitHub signs every webhook payload with a secret key using HMAC-SHA256.
    We re-compute the same hash locally and compare. If they match, the
    request genuinely came from GitHub — not a third party attacker.
"""

import hashlib
import hmac
import logging

from src.config import WEBHOOK_SECRET

logger = logging.getLogger(__name__)


def verify_github_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """
    Verifies the HMAC-SHA256 signature on an incoming GitHub webhook request.

    Args:
        payload_body:     Raw bytes of the HTTP request body.
        signature_header: Value of the 'X-Hub-Signature-256' header from GitHub.
                          Expected format: 'sha256=<hex_digest>'

    Returns:
        True  → Signature is valid (or WEBHOOK_SECRET is not configured).
        False → Signature is missing or does not match. REJECT the request.
    """
    if not WEBHOOK_SECRET:
        # Allow requests through in local dev when no secret is set.
        # A startup warning in config.py already alerts the developer.
        return True

    if not signature_header:
        logger.warning("🚨 Request is missing the X-Hub-Signature-256 header.")
        return False

    # Compute expected signature using our secret key
    expected_signature = "sha256=" + hmac.new(
        key=WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # hmac.compare_digest prevents timing-based side-channel attacks
    is_valid = hmac.compare_digest(expected_signature, signature_header)

    if not is_valid:
        logger.warning("🚨 Signature mismatch — request may be forged.")

    return is_valid

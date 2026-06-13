"""
github_client.py — GitHub API Integration Module.

Responsibility: All communication with the GitHub API lives here.
No other module should ever import PyGithub or call GitHub APIs directly.

Public functions:
  - get_pr_diff()      → Fetch the raw code diff for a Pull Request.
  - post_pr_comment()  → Post a Markdown review comment on a Pull Request.
"""

import logging

from github import Github, GithubException

from src.config import GITHUB_TOKEN

logger = logging.getLogger(__name__)

# Single shared GitHub client instance (reused across all requests)
_github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None  #creating an authenticated GitHub client.


#  PRIVATE: Get GitHub client (with safety check)

def _get_client() -> Github:
    """
    Returns the shared GitHub client.
    Raises RuntimeError if GITHUB_TOKEN is not configured.
    """
    if not _github_client:
        raise RuntimeError(
            "GITHUB_TOKEN is not set. Cannot connect to GitHub API. "
            "Please add it to your .env file."
        )
    return _github_client


#  PUBLIC: Fetch PR Diff

async def get_pr_diff(repo_full_name: str, pr_number: int) -> str:
    """
    Fetches the unified diff (code changes) for a GitHub Pull Request.

    This is the raw text showing which lines were added (+) or removed (-)
    across all files in the PR. This diff is what we feed to the AI agent.

    Args:
        repo_full_name: Full name of the repository e.g. "alice/my-project"
        pr_number:      The Pull Request number e.g. 42

    Returns:
        A string containing the unified diff text.
        Returns an empty string if the diff cannot be fetched.
    """
    try:
        client = _get_client()
        repo = client.get_repo(repo_full_name)
        
        pull_request = repo.get_pull(pr_number)

        # Build a readable diff string from all changed files in the PR
        diff_parts = []

        for file in pull_request.get_files():
            # Skip binary files, deletions, and files with no patch
            if not file.patch:
                continue

            diff_parts.append(
                f"### File: `{file.filename}`\n"
                f"Status: {file.status} | "
                f"+{file.additions} additions, -{file.deletions} deletions\n\n"
                f"```diff\n{file.patch}\n```\n"
            )

        if not diff_parts:
            logger.info(f"ℹ️  PR #{pr_number} has no reviewable code changes (binary or empty files only).")
            return ""

        diff_text = "\n---\n".join(diff_parts)

        logger.info(
            f"📦 Fetched diff for PR #{pr_number}: "
            f"{pull_request.changed_files} file(s) changed."
        )
        return diff_text

    except GithubException as e:
        logger.error(f"❌ GitHub API error fetching diff for PR #{pr_number}: {e.status} — {e.data}")
        return ""
    except RuntimeError as e:
        logger.error(f"❌ Configuration error: {e}")
        return ""
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching diff for PR #{pr_number}: {e}")
        return ""


#  PUBLIC: Post PR Comment

async def post_pr_comment(repo_full_name: str, pr_number: int, comment_body: str) -> bool:
    """
    Posts a Markdown-formatted review comment on a GitHub Pull Request.

    The comment appears in the PR's "Conversation" tab, exactly like a
    human reviewer would post it.

    Args:
        repo_full_name: Full name of the repository e.g. "alice/my-project"
        pr_number:      The Pull Request number e.g. 42
        comment_body:   The Markdown string to post as a comment.

    Returns:
        True  → Comment posted successfully.
        False → An error occurred.
    """
    try:
        client = _get_client()
        repo = client.get_repo(repo_full_name)
        pull_request = repo.get_pull(pr_number)

        # Post the comment on the PR conversation thread
        pull_request.create_issue_comment(comment_body)

        logger.info(f"💬 Review comment posted on PR #{pr_number} in '{repo_full_name}'")
        return True

    except GithubException as e:
        logger.error(f"❌ GitHub API error posting comment on PR #{pr_number}: {e.status} — {e.data}")
        return False
    except RuntimeError as e:
        logger.error(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error posting comment on PR #{pr_number}: {e}")
        return False

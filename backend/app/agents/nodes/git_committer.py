"""
git_committer.py

Agent node responsible for committing and pushing AI-generated fixes.
Uses GitHubClient for all git operations and enforces branch safety.
"""

import logging

from app.integrations.github_client import GitHubClient

logger = logging.getLogger(__name__)


class NoChangesDetectedError(Exception):
    """Raised when there are no staged or unstaged changes to commit."""


def commit_fix(repo_path: str, message: str) -> None:
    """
    Stage all changes, commit with a prefixed message, and push.

    The commit message is automatically formatted as::

        [AI-AGENT] Fix SYNTAX error in file line X

    where *message* supplies the descriptive portion.

    Args:
        repo_path: Absolute path to the local git repository.
        message:   Descriptive part of the commit message
                   (the ``[AI-AGENT]`` prefix is added by GitHubClient).

    Raises:
        NoChangesDetectedError: If the working tree has no changes.
        BranchProtectionError:  If the current branch is ``main`` or ``master``.
        GitCommandError:        On any underlying git failure.
    """
    client = GitHubClient(repo_path)
    repo = client.repo

    # ── Verify there are actual changes to commit ────────────────────
    if not repo.is_dirty(untracked_files=True):
        msg = "No changes detected in the working tree. Nothing to commit."
        logger.error(msg)
        raise NoChangesDetectedError(msg)

    logger.info("Changes detected – preparing commit.")

    # commit_all already enforces branch protection and adds [AI-AGENT] prefix
    client.commit_all(message)
    logger.info("Changes committed successfully.")

    # ── Push to remote ───────────────────────────────────────────────
    client.push_current_branch()
    logger.info("Changes pushed to remote.")

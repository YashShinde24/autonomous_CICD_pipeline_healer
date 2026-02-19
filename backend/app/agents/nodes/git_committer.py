"""
git_committer.py

Agent node responsible for committing and pushing AI-generated fixes.
Uses GitHubClient for all git operations and enforces branch safety.
"""

import logging

from app.integrations.github_client import GitHubClient
from app.core.database import create_fix, SessionLocal

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


def run(state):
    """Commit and push fixes to the repository, and save fix records to database."""
    repo_path = state.get("repo_path", ".")
    message = state.get("commit_message", "Automated fix applied")
    
    try:
        commit_fix(repo_path, message)
        state["commit_count"] = state.get("commit_count", 0) + 1
        state["logs"].append("Changes committed and pushed")
        
        # Save fix records to database
        run_id = state.get("run_id")
        classified_failures = state.get("classified_failures", [])
        if run_id and classified_failures:
            db = SessionLocal()
            try:
                for failure in classified_failures:
                    # Parse the classified failure string
                    parts = failure.split(" ")
                    bug_type = parts[0] if parts else "SYNTAX"
                    file_path = ""
                    line_number = None
                    
                    # Try to extract file and line from format: "BUG_TYPE error in file line N"
                    if "error in" in failure and "line" in failure:
                        try:
                            after_in = failure.split("error in ")[1]
                            file_line = after_in.split(" line ")
                            file_path = file_line[0].strip()
                            line_str = file_line[1].split(" ")[0].strip()
                            line_number = int(line_str) if line_str.isdigit() else None
                        except (IndexError, ValueError):
                            pass
                    
                    create_fix(
                        db=db,
                        run_id=run_id,
                        file=file_path or "unknown",
                        bug_type=bug_type if bug_type in ["LINTING", "SYNTAX", "LOGIC", "TYPE_ERROR", "IMPORT", "INDENTATION"] else "SYNTAX",
                        line_number=line_number,
                        commit_message=f"[AI-AGENT] {message}",
                        status="FIXED"
                    )
            except Exception as e:
                logger.error("Failed to save fix to database: %s", e)
                db.rollback()
            finally:
                db.close()
                
    except Exception as e:
        state["logs"].append(f"Commit failed: {str(e)}")
        
        # Save failed fix to database
        run_id = state.get("run_id")
        if run_id:
            db = SessionLocal()
            try:
                create_fix(
                    db=db,
                    run_id=run_id,
                    file="unknown",
                    bug_type="SYNTAX",
                    status="FAILED"
                )
            except Exception as db_err:
                logger.error("Failed to save failed fix to database: %s", db_err)
                db.rollback()
            finally:
                db.close()
    
    return state

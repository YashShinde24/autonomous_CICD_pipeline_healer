"""
ci_monitor.py

Agent node wrapper over CIProvider.
Fetches the latest workflow run status and returns a normalised result.
"""

import logging

from app.integrations.ci_provider import CIProvider, CIProviderError

logger = logging.getLogger(__name__)


def monitor_ci(ci_provider: CIProvider) -> dict:
    """
    Query the latest CI workflow run and return a normalised status.

    Args:
        ci_provider: An initialised CIProvider instance.

    Returns:
        A dict with keys:
            - completed (bool): True if the workflow run has finished.
            - success (bool):   True if the conclusion is "success".
            - raw_status (dict): The original dict from CIProvider.
    """
    try:
        raw = ci_provider.get_latest_workflow_status()
    except CIProviderError as exc:
        logger.error("Failed to fetch CI status: %s", exc)
        return {
            "completed": False,
            "success": False,
            "raw_status": {"status": "error", "conclusion": None},
        }

    status = raw.get("status", "unknown")
    conclusion = raw.get("conclusion")

    completed = status == "completed"
    success = completed and conclusion == "success"

    logger.info(
        "CI monitor – completed: %s, success: %s (status=%s, conclusion=%s)",
        completed,
        success,
        status,
        conclusion,
    )

    return {
        "completed": completed,
        "success": success,
        "raw_status": raw,
    }

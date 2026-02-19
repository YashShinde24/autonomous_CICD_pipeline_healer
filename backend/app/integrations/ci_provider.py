"""
ci_provider.py

Fetch the latest GitHub Actions workflow run status for a repository
using the GitHub REST API via the ``requests`` library.
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class CIProviderError(Exception):
    """Raised when a CI provider operation fails."""


class CIProvider:
    """Read-only client for querying GitHub Actions workflow status."""

    def __init__(
        self, repo_owner: str, repo_name: str, github_token: str
    ) -> None:
        """
        Initialise the CI provider.

        Args:
            repo_owner:   GitHub organisation or user name.
            repo_name:    Repository name.
            github_token: Personal-access or fine-grained token with
                          ``actions:read`` scope.
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self._headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        logger.info(
            "CIProvider initialised for %s/%s", repo_owner, repo_name
        )

    # ── Public API ───────────────────────────────────────────────────

    def get_latest_workflow_status(self) -> dict:
        """
        Return the status and conclusion of the most recent workflow run.

        Returns:
            A dict with keys:
                - status (str):            e.g. "completed", "in_progress", "queued"
                - conclusion (str | None): e.g. "success", "failure", None
                - error (str | None):      Error message if the request failed

        Raises:
            CIProviderError: On unrecoverable API or network failures.
        """
        url = (
            f"{GITHUB_API_BASE}/repos/"
            f"{self.repo_owner}/{self.repo_name}/actions/runs"
        )
        params = {"per_page": 1}

        try:
            response = requests.get(
                url, headers=self._headers, params=params, timeout=30
            )
            response.raise_for_status()

        except requests.ConnectionError as exc:
            msg = f"Network error while contacting GitHub API: {exc}"
            logger.error(msg)
            raise CIProviderError(msg) from exc

        except requests.Timeout as exc:
            msg = "GitHub API request timed out."
            logger.error(msg)
            raise CIProviderError(msg) from exc

        except requests.HTTPError as exc:
            msg = (
                f"GitHub API returned HTTP {response.status_code}: "
                f"{response.text}"
            )
            logger.error(msg)
            raise CIProviderError(msg) from exc

        # ── Parse response ───────────────────────────────────────────
        data = response.json()
        runs = data.get("workflow_runs", [])

        if not runs:
            logger.warning(
                "No workflow runs found for %s/%s.",
                self.repo_owner,
                self.repo_name,
            )
            return {
                "status": "none",
                "conclusion": None,
            }

        latest = runs[0]
        status: str = latest.get("status", "unknown")
        conclusion: Optional[str] = latest.get("conclusion")

        logger.info(
            "Latest run – status: %s, conclusion: %s", status, conclusion
        )

        return {
            "status": status,
            "conclusion": conclusion,
        }

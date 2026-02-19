"""
test_executor.py

Agent node that delegates pytest execution to ``docker_sandbox``
and returns a normalised, structured result.
"""

import logging

from app.core.docker_sandbox import run_pytest_in_docker

logger = logging.getLogger(__name__)


def execute_tests(repo_path: str) -> dict:
    """
    Run pytest against a repository and return a normalised result.

    Args:
        repo_path: Absolute path to the repository to test.

    Returns:
        A dict with keys:
            - passed (bool):  True if all tests passed.
            - logs (str):     Combined standard output from pytest.
            - errors (str):   Combined stderr and any error messages.
    """
    logger.info("Executing tests for repo: %s", repo_path)

    raw = run_pytest_in_docker(repo_path)

    passed = raw.get("success", False)
    logs = (raw.get("stdout") or "").strip()
    stderr = (raw.get("stderr") or "").strip()
    error = (raw.get("error") or "").strip()

    # Merge stderr and error into a single errors field
    error_parts = [part for part in (stderr, error) if part]
    errors = "\n".join(error_parts)

    if passed:
        logger.info("All tests passed.")
    else:
        logger.warning("Tests failed or encountered errors.")

    return {
        "passed": passed,
        "logs": logs,
        "errors": errors,
    }


def run(state):
    """Execute tests and update state with results."""
    repo_path = state.get("repo_path", ".")
    
    result = execute_tests(repo_path)
    
    state["passed"] = result["passed"]
    state["logs"] = result["logs"]
    state["errors"] = result["errors"]
    state["test_errors"] = result["errors"]
    state["logs"].append(f"Tests executed: {'passed' if result['passed'] else 'failed'}")
    
    return state

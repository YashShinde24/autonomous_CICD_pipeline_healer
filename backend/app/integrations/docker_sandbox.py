"""
docker_sandbox.py

Safely execute pytest inside a repository directory using subprocess.
Captures stdout, stderr and handles timeouts gracefully.
"""

import subprocess
import logging
import os

logger = logging.getLogger(__name__)


def run_pytest(repo_path: str, timeout: int = 120) -> dict:
    """
    Run pytest inside the given repository directory.

    Args:
        repo_path: Absolute path to the repository directory.
        timeout: Maximum seconds to allow pytest to run before killing it.

    Returns:
        A structured dict with keys:
            - success (bool): True if pytest exited with code 0.
            - exit_code (int): The process exit code (-1 if not available).
            - stdout (str): Captured standard output.
            - stderr (str): Captured standard error.
            - error (str | None): Error message if something went wrong.
    """
    result = {
        "success": False,
        "exit_code": -1,
        "stdout": "",
        "stderr": "",
        "error": None,
    }

    # ── Validate repo path ──────────────────────────────────────────
    if not os.path.isdir(repo_path):
        msg = f"Repository path does not exist or is not a directory: {repo_path}"
        logger.error(msg)
        result["error"] = msg
        return result

    try:
        logger.info("Running pytest in: %s (timeout=%ds)", repo_path, timeout)

        process = subprocess.run(
            ["python", "-m", "pytest", "--tb=short", "-q"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        result["exit_code"] = process.returncode
        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        result["success"] = process.returncode == 0

        if result["success"]:
            logger.info("pytest passed successfully.")
        else:
            logger.warning(
                "pytest failed with exit code %d.", process.returncode
            )

    except subprocess.TimeoutExpired as exc:
        msg = f"pytest timed out after {timeout} seconds."
        logger.error(msg)
        result["error"] = msg
        result["stdout"] = str(exc.stdout) if exc.stdout else ""
        result["stderr"] = str(exc.stderr) if exc.stderr else ""

    except FileNotFoundError:
        msg = "Python executable not found. Ensure Python is installed and on PATH."
        logger.error(msg)
        result["error"] = msg

    except OSError as exc:
        msg = f"OS error while running pytest: {exc}"
        logger.error(msg)
        result["error"] = msg

    except Exception as exc:            # noqa: BLE001 – intentional broad catch
        msg = f"Unexpected error while running pytest: {exc}"
        logger.exception(msg)
        result["error"] = msg

    return result

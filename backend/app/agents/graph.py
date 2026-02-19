"""
graph.py

LangGraph StateGraph pipeline for the autonomous CI/CD healing loop.

Flow:
    START → run_tests
        → if passed  → END (status: "passed")
        → if failed  → commit_fix → push_branch → monitor_ci
            → if CI passed  → END (status: "fixed")
            → if CI failed  → retry_decision
                → should_retry True  → run_tests (loop)
                → should_retry False → END (status: "failed")
"""

import logging
from datetime import datetime

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.nodes.test_executor import execute_tests
from app.agents.nodes.git_committer import commit_fix
from app.agents.nodes.ci_monitor import monitor_ci
from app.integrations.github_client import GitHubClient
from app.integrations.ci_provider import CIProvider
from app.core.retry_manager import RetryManager

logger = logging.getLogger(__name__)


# ── Node wrappers ────────────────────────────────────────────────────


def node_run_tests(state: AgentState) -> dict:
    """Execute pytest inside Docker and update state."""
    logger.info("Node: run_tests (iteration %d)", state.get("iteration", 0))

    result = execute_tests(state["repo_url"])

    logs = list(state.get("logs") or [])
    logs.append(f"[run_tests] passed={result['passed']}")

    update: dict = {
        "ci_status": "passed" if result["passed"] else "failed",
        "logs": logs,
    }

    if not result["passed"]:
        failures = list(state.get("failures") or [])
        failures.append({
            "iteration": state.get("iteration", 0),
            "errors": result.get("errors", ""),
        })
        update["failures"] = failures

    if result["passed"]:
        update["final_status"] = "passed"
        update["end_time"] = datetime.utcnow().isoformat()

    return update


def node_commit_fix(state: AgentState) -> dict:
    """Stage and commit the AI-generated fix."""
    logger.info("Node: commit_fix")

    message = f"Fix iteration {state.get('iteration', 0)}"
    try:
        commit_fix(state["repo_url"], message)
    except Exception as exc:
        logger.error("commit_fix failed: %s", exc)
        logs = list(state.get("logs") or [])
        logs.append(f"[commit_fix] error: {exc}")
        return {"logs": logs}

    applied = list(state.get("applied_fixes") or [])
    applied.append(message)

    logs = list(state.get("logs") or [])
    logs.append(f"[commit_fix] committed: {message}")

    return {"applied_fixes": applied, "logs": logs}


def node_push_branch(state: AgentState) -> dict:
    """Push the current feature branch to origin."""
    logger.info("Node: push_branch")

    try:
        client = GitHubClient(state["repo_url"])
        client.push_current_branch()
    except Exception as exc:
        logger.error("push_branch failed: %s", exc)
        logs = list(state.get("logs") or [])
        logs.append(f"[push_branch] error: {exc}")
        return {"logs": logs}

    logs = list(state.get("logs") or [])
    logs.append("[push_branch] pushed successfully")
    return {"logs": logs}


def node_monitor_ci(state: AgentState) -> dict:
    """Poll the GitHub Actions workflow status."""
    logger.info("Node: monitor_ci")

    # Extract owner/repo from repo_url
    # Expects format: https://github.com/owner/repo or owner/repo
    repo_url: str = state.get("repo_url", "")
    parts = repo_url.rstrip("/").split("/")
    owner = parts[-2] if len(parts) >= 2 else ""
    repo = parts[-1].replace(".git", "") if parts else ""

    import os
    token = os.environ.get("GITHUB_TOKEN", "")

    provider = CIProvider(owner, repo, token)
    result = monitor_ci(provider)

    ci_status = "passed" if result.get("success") else "failed"

    logs = list(state.get("logs") or [])
    logs.append(f"[monitor_ci] completed={result.get('completed')}, success={result.get('success')}")

    update: dict = {"ci_status": ci_status, "logs": logs}

    if result.get("success"):
        update["final_status"] = "fixed"
        update["end_time"] = datetime.utcnow().isoformat()

    return update


def node_retry_decision(state: AgentState) -> dict:
    """Decide whether to retry the healing loop."""
    iteration = state.get("iteration", 0)
    max_retries = state.get("max_retries", 2)

    manager = RetryManager(max_retries=max_retries)
    # Fast-forward the manager to the current attempt count
    for _ in range(iteration):
        manager.track_attempt()

    should = manager.should_retry("failure")

    logs = list(state.get("logs") or [])

    if should:
        manager.track_attempt()
        new_iteration = iteration + 1
        logs.append(f"[retry_decision] retrying (attempt {new_iteration}/{max_retries})")
        return {"iteration": new_iteration, "logs": logs}
    else:
        logs.append(f"[retry_decision] max retries exceeded ({iteration}/{max_retries})")
        return {
            "final_status": "failed",
            "end_time": datetime.utcnow().isoformat(),
            "logs": logs,
        }


# ── Conditional edge functions ───────────────────────────────────────


def after_tests(state: AgentState) -> str:
    """Route after test execution."""
    if state.get("ci_status") == "passed":
        return END
    return "commit_fix"


def after_ci(state: AgentState) -> str:
    """Route after CI monitoring."""
    if state.get("ci_status") == "passed":
        return END
    return "retry_decision"


def after_retry(state: AgentState) -> str:
    """Route after retry decision."""
    if state.get("final_status") == "failed":
        return END
    return "run_tests"


# ── Graph construction ───────────────────────────────────────────────


def compile() -> object:
    """Build and compile the LangGraph healing pipeline.

    Returns:
        A compiled LangGraph runnable.
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("run_tests", node_run_tests)
    graph.add_node("commit_fix", node_commit_fix)
    graph.add_node("push_branch", node_push_branch)
    graph.add_node("monitor_ci", node_monitor_ci)
    graph.add_node("retry_decision", node_retry_decision)

    # Entry point
    graph.set_entry_point("run_tests")

    # Edges
    graph.add_conditional_edges("run_tests", after_tests)
    graph.add_edge("commit_fix", "push_branch")
    graph.add_edge("push_branch", "monitor_ci")
    graph.add_conditional_edges("monitor_ci", after_ci)
    graph.add_conditional_edges("retry_decision", after_retry)

    logger.info("Healing pipeline compiled.")
    return graph.compile()

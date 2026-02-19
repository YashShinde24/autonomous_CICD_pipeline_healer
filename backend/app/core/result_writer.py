import json
from datetime import datetime
from app.core.scoring_engine import calculate_score

RESULT_PATH = "app/results/results.json"

def save_results(state):
    total_time = (
        datetime.fromisoformat(state["end_time"]) -
        datetime.fromisoformat(state["start_time"])
    ).total_seconds()

    score = calculate_score(total_time, state["commit_count"])

    result = {
        "repository": state["repo_url"],
        "branch": state["branch_name"],
        "failures_detected": len(state["failures"]),
        "fixes_applied": len(state["applied_fixes"]),
        "iterations": state["iteration"],
        "final_status": state["ci_status"],
        "time_taken": f"{int(total_time)} seconds",
        "score": score
    }

    with open(RESULT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    state["score"] = score
    return state

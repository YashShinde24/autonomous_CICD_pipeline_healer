def run(state):
    # Simulated CI behavior

    if state["iteration"] < 2:
        state["ci_status"] = "FAILED"
        state["failures"] = [
            {"file": "app.py", "line": 10, "error": "SyntaxError: invalid syntax"}
        ]
    else:
        state["ci_status"] = "PASSED"

    state["logs"].append(f"CI status: {state['ci_status']}")
    return state

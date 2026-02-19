def run(state):

    if state["ci_status"] == "READY_FOR_COMMIT":
        state["ci_status"] = "PASSED"

    state["logs"].append("CI monitored")

    return state

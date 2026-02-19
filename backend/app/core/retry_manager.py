def should_retry(state):
    return state["iteration"] < state["max_retries"]

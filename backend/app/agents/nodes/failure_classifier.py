from app.integrations.groq_client import call_groq
from app.core.test_case_formatter import reconstruct_format

SYSTEM_PROMPT = """You are an automated CI/CD failure classification engine.

Your job is to strictly classify test failures into one of the following bug types:

LINTING
SYNTAX
LOGIC
TYPE_ERROR
IMPORT
INDENTATION

Output format (STRICT):
{BUG_TYPE} error in {file_path} line {line_number} → Fix: {short fix description}
"""

def classify_failure(file_path, line_number, error_message):
    user_prompt = f"""Test failure detected:

File: {file_path}
Line: {line_number}
Error Message: {error_message}

Classify this failure and generate formatted output.
"""

    raw = call_groq(SYSTEM_PROMPT, user_prompt)
    return reconstruct_format(raw)


def run(state):
    """Classify failures in the state and update classified_failures."""
    failures = state.get("failures", [])
    classified = []

    for failure in failures:
        result = classify_failure(
            failure.get("file", ""),
            failure.get("line", 0),
            failure.get("error", "")
        )
        classified.append(result)

    state["classified_failures"] = classified
    state["logs"].append(f"Classified {len(classified)} failures")
    return state

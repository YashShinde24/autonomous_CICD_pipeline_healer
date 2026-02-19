import ast

def validate_fix(original_content, updated_content, classified_failure):

    if original_content == updated_content:
        return "INVALID: no changes made"

    try:
        ast.parse(updated_content)
    except SyntaxError:
        return "INVALID: syntax error introduced"

    bug_type = classified_failure.split(" ")[0]
    if bug_type not in ["LINTING", "SYNTAX", "LOGIC", "TYPE_ERROR", "IMPORT", "INDENTATION"]:
        return "INVALID: mismatch failure"

    return "VALID"


def run(state):
    """Validate fixes generated for classified failures."""
    classified_failures = state.get("classified_failures", [])
    applied_fixes = state.get("applied_fixes", [])
    
    validation_results = []
    for failure, fix in zip(classified_failures, applied_fixes):
        result = validate_fix("original", fix, failure)
        validation_results.append(result)
    
    state["validation_results"] = validation_results
    state["logs"].append(f"Validated {len(validation_results)} fixes")
    return state

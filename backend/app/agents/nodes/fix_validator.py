import ast

def validate_fix(original_content, updated_content, classified_failure):

    if original_content == updated_content:
        return "INVALID: no changes made"

    try:
        ast.parse(updated_content)
    except:
        return "INVALID: syntax error introduced"

    if classified_failure.split(" ")[0] not in classified_failure:
        return "INVALID: mismatch failure"

    return "VALID"

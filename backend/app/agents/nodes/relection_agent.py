from app.integrations.groq_client import call_groq

SYSTEM_PROMPT = """You are a reflection agent in a multi-agent CI healing system.

The previous fix attempt failed.
Return short actionable correction strategy.
"""

def reflect(classified_failure, previous_patch, new_error):
    user_prompt = f"""
Previous failure classification:
{classified_failure}

Previous fix attempt:
{previous_patch}

New CI error:
{new_error}
"""
    return call_groq(SYSTEM_PROMPT, user_prompt)

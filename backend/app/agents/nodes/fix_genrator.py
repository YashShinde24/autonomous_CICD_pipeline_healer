from app.integrations.groq_client import call_groq

SYSTEM_PROMPT = """You are an autonomous DevOps CI healing agent.

Rules:
- Only modify the necessary lines.
- Do NOT change unrelated code.
- Maintain original formatting.
- Do NOT add comments.
- Return the full updated file content only.
"""

def generate_fix(file_content, formatted_failure):
    user_prompt = f"""Original file content:

{file_content}

Failure:
{formatted_failure}

Generate corrected full file content.
"""

    return call_groq(SYSTEM_PROMPT, user_prompt)

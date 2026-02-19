from app.core.guard import generate_branch

def validate_branch(team, leader, branch):
    if branch != generate_branch(team, leader):
        raise Exception("Invalid branch format")

def validate_commit_message(message):
    if not message.startswith("[AI-AGENT]"):
        raise Exception("Invalid commit message")

def validate_retry(iteration, max_retries):
    if iteration > max_retries:
        raise Exception("Retry limit exceeded")

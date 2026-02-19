from typing import TypedDict, List
from datetime import datetime

class AgentState(TypedDict):
    repo_url: str
    team_name: str
    leader_name: str
    branch_name: str
    iteration: int
    max_retries: int
    failures: List[dict]
    classified_failures: List[str]
    applied_fixes: List[str]
    ci_status: str
    logs: List[str]
    start_time: str
    end_time: str
    score: int

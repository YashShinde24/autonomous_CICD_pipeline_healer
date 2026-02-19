def generate_branch(team: str, leader: str):
    team = team.upper().replace(" ", "_")
    leader = leader.upper().replace(" ", "_")
    return f"{team}_{leader}_AI_Fix"

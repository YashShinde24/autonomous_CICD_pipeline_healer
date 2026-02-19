"""Module for generating standardized Git branch names."""

import re


def generate_branch(team_name: str, leader_name: str) -> str:
    """Generate a standardized branch name from team and leader names.

    The branch name follows the format: TEAMNAME_LEADERNAME_AI_FIX
    All characters are uppercased, non-alphanumeric characters are replaced
    with underscores, and consecutive/trailing underscores are collapsed/removed.

    Args:
        team_name: The name of the team.
        leader_name: The name of the team leader.

    Returns:
        A formatted branch name string.

    Raises:
        ValueError: If team_name or leader_name is empty or whitespace-only.
        TypeError: If team_name or leader_name is not a string.
    """
    if not isinstance(team_name, str) or not isinstance(leader_name, str):
        raise TypeError("team_name and leader_name must be strings.")

    if not team_name.strip():
        raise ValueError("team_name must not be empty or whitespace-only.")
    if not leader_name.strip():
        raise ValueError("leader_name must not be empty or whitespace-only.")

    def _sanitize(value: str) -> str:
        """Replace non-alphanumeric characters with underscores and clean up."""
        upper = value.upper().strip()
        cleaned = re.sub(r"[^A-Z0-9]", "_", upper)   # replace non-alnum
        cleaned = re.sub(r"_+", "_", cleaned)          # collapse consecutive _
        cleaned = cleaned.strip("_")                    # remove leading/trailing _
        return cleaned

    team = _sanitize(team_name)
    leader = _sanitize(leader_name)

    branch = f"{team}_{leader}_AI_FIX"
    return branch

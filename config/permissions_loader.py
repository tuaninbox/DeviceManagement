# app/auth/permissions.py

import yaml
from pathlib import Path

def load_permissions_file():
    yaml_path = Path(__file__).parent / "permissions.yaml"
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)

# Load YAML once
_raw = load_permissions_file()

PERMISSIONS = _raw["permissions"]
ROLE_INHERITANCE = _raw.get("inheritance", {})

def expand_roles(roles: list[str]) -> set[str]:
    """
    Expand roles using inheritance rules.
    Example:
        admin -> operator -> user
    """
    expanded = set(roles)
    stack = list(roles)

    while stack:
        role = stack.pop()
        inherited = ROLE_INHERITANCE.get(role, [])
        for r in inherited:
            if r not in expanded:
                expanded.add(r)
                stack.append(r)

    return expanded

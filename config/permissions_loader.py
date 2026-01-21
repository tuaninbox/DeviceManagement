import yaml
from pathlib import Path


def load_permissions_file():
    yaml_path = Path(__file__).parent / "permissions.yaml"
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


# Load YAML once
_raw = load_permissions_file()

PERMISSIONS = _raw.get("permissions", {})
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


def get_allowed_commands(role: str, vendor: str, os: str, platform: str) -> list[str]:
    """
    Returns allowed commands for a given:
    - role
    - vendor (cisco, dell, juniper, etc.)
    - os (ios, iosxe, nxos, junos, etc.)
    - platform (router, switch, firewall, etc.)

    Supports role inheritance automatically.
    """

    # Expand inherited roles (admin → operator → user)
    expanded = expand_roles([role])

    allowed = []

    for r in expanded:
        role_cmds = (
            PERMISSIONS
                .get("commands", {})
                .get(r, {})
                .get(vendor, {})
                .get(os, {})
                .get(platform, [])
        )
        allowed.extend(role_cmds)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for cmd in allowed:
        if cmd not in seen:
            seen.add(cmd)
            unique.append(cmd)

    return unique

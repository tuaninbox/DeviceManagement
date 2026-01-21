from typing import List

from config.permissions_loader import get_allowed_commands
from core.executor import run_commands_on_device
from app.models.devices import Device


def get_allowed_commands_for_device(
    role: str,
    device: Device
) -> List[str]:
    """
    Returns the list of commands allowed for this role + device classification.
    """
    return get_allowed_commands(
        role=role,
        vendor=device.vendor,
        os=device.os,
        platform=device.platform
    )


def validate_commands(
    requested: List[str],
    allowed: List[str]
) -> None:
    """
    Ensures all requested commands are permitted for this role/device type.
    Raises PermissionError if any command is not allowed.
    """
    for cmd in requested:
        if cmd not in allowed:
            raise PermissionError(
                f"Command '{cmd}' is not allowed for this role/device type"
            )

def executor_commands(
    device: Device,
    commands: List[str],
    username: str,
    password: str
) -> List[dict]:
    """
    Delegates execution to core.executor.run_commands_on_device().
    Returns a list of {command, result}.
    """
    return run_commands_on_device(
        device=device,
        commands=commands,
        username=username,
        password=password
    )

from typing import List
from pydantic import BaseModel


class RunCommandRequest(BaseModel):
    """
    Request body for running commands on a specific device.
    """
    device_id: int
    commands: List[str]


class CommandResult(BaseModel):
    """
    Single command execution result.
    """
    command: str
    result: str


class DeviceCommandResponse(BaseModel):
    """
    Response format when running commands on a device.

    {
      "device": "switch01",
      "commands": [
        { "command": "show version", "result": "..." },
        { "command": "show ip interface brief", "result": "..." }
      ]
    }
    """
    device: str
    commands: List[CommandResult]


class AvailableCommandsResponse(BaseModel):
    """
    Commands available to the current user for a given device classification.
    This is what your /commands/available endpoint can return.
    """
    role: str
    vendor: str
    os: str
    platform: str
    commands: List[str]

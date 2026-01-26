# routers/commands.py
from .. import databases
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..schemas.commands import (
    RunCommandRequest,
    DeviceCommandResponse,
    AvailableCommandsResponse,
)
from ..services.command_manager import (
    get_allowed_commands_for_device,
    validate_commands,
    run_commands_on_device,
)
from ..models.devices import Device
from ..auth.dependencies import get_current_user


router = APIRouter(prefix="/commands", tags=["Commands"])


# Dependency for DB session
def get_db():
    db = databases.devices.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------
# GET /commands/available?device_id=123
# ------------------------------------------------------------
@router.get("/available", response_model=AvailableCommandsResponse)
def get_available_commands(
    device_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Returns the list of commands the current user is allowed to run
    on the specified device (based on role + vendor + os + platform).
    """

    device: Device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    allowed = get_allowed_commands_for_device(
        role=user.role,
        device=device
    )

    return AvailableCommandsResponse(
        role=user.role,
        vendor=device.vendor,
        os=device.os,
        platform=device.platform,
        commands=allowed,
    )


# ------------------------------------------------------------
# POST /commands/run
# ------------------------------------------------------------
@router.post("/run", response_model=DeviceCommandResponse)
def run_commands(
    payload: RunCommandRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Validates and executes commands on a device.
    """

    # 1. Load device
    device: Device = db.query(Device).filter(Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # 2. Get allowed commands for this user + device type
    allowed = get_allowed_commands_for_device(
        role=user.role,
        device=device
    )

    # 3. Validate requested commands
    try:
        validate_commands(payload.commands, allowed)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # 4. Execute commands
    results = run_commands_on_device(
        device=device,
        commands=payload.commands,
        username=user.username,
        password=user.password,  # or however you store device creds
    )

    # 5. Return structured response
    return DeviceCommandResponse(
        device=device.hostname,
        commands=results,
    )

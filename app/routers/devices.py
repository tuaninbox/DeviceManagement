from app.databases import devices
from app.models import devices
from app.schemas import devices
from fastapi import APIRouter, Depends, HTTPException
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func
from app.services.job_manager import create_job
from app.services.device_sync import run_device_sync
from app import crud
from app.normalizers.device_normalizer import (
    normalize_device,
    normalize_interfaces,
    normalize_modules,
    normalize_software_info,
)
from core.logging_manager import setup_loggers
from config.config_loader import load_device_management_config
from core.utility.utility import safe_read_text, MAX_FILE_BYTES

# Set up loggers
success_logger, fail_logger = setup_loggers(logger_name="app_router_devices")

router = APIRouter(prefix="/devices", tags=["devices"])

def get_db_session_factory():
    """
    Returns a callable that creates new DB sessions.
    Useful for background tasks where request-scoped DB sessions are closed.
    """
    return devices.SessionLocal

# Dependency for DB session
def get_db():
    db = devices.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=devices.Device)
def create_device(device: devices.DeviceCreate, db: Session = Depends(get_db)):
    success_logger.info(f"Creating device: {device.hostname}")
    return crud.create_device(db=db, device=device)


# Get all devices
# @router.get("/", response_model=List[schemas.Device])
@router.get("/", response_model=devices.DeviceListResponse)
def list_devices(page: int = 1,page_size: int = 100,db: Session = Depends(get_db)):
    success_logger.info(f"Listing devices page {page} with {page_size} devices")
    
    # Convert page → skip
    skip = (page - 1) * page_size

    # Query total count
    total = db.query(devices.Device).count()

    # Query paginated items
    items = crud.get_devices(db, skip=skip, limit=page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.get("/all", response_model=List[devices.Device])
def list_all_devices(db: Session = Depends(get_db)):
    success_logger.info("Listing ALL devices")
    return crud.get_all_devices(db)


@router.get("/{hostname}", response_model=devices.Device)
def get_device_by_hostname(hostname: str, db: Session = Depends(get_db)):
    success_logger.info(f"Fetching device by hostname: {hostname}")
    device = (
        db.query(devices.Device)
        .filter(func.lower(devices.Device.hostname) == hostname.lower())
        .first()
    )

    if not device:
        fail_logger.warning(f"Device '{hostname}' not found")
        raise HTTPException(
            status_code=404,
            detail=f"Device '{hostname}' not found"
        )

    return device

# Get configuration and operational data
@router.get("/{hostname}/configops", response_model=devices.DeviceConfigOpsEnvelope)
def get_device_config_ops(
    hostname: str,
    db: Session = Depends(get_db),
    max_bytes: int = MAX_FILE_BYTES,  # allow clients to limit returned size
):
    """
    Returns configuration and operational data for a single device.
    Reads from running_config_path and routing_table_path.
    Response is wrapped with { success, result, message }.
    Does not raise 404; returns success=False in not-found case for uniformity.
    """

    device = (
        db.query(devices.Device)
        .filter(func.lower(devices.Device.hostname) == hostname.lower())
        .first()
    )

    if not device:
        return {
            "success": False,
            "result": None,
            "message": f"Device {hostname} not found",
        }

    configuration = safe_read_text(
        getattr(device, "running_config_path", None),
        max_bytes=max_bytes
    )
    operationaldata = safe_read_text(
        getattr(device, "routing_table_path", None),
        max_bytes=max_bytes
    )

    result = devices.DeviceConfigOps(
        device=getattr(device, "name", f"{hostname}"),
        configuration=configuration,
        operationaldata=operationaldata,
    )

    return {
        "success": True,
        "result": result,
        "message": "Configuration and operational data fetched",
    }


# Sync Devices
@router.post("/sync")
def sync_devices(
    request: devices.SyncRequest,
    background: BackgroundTasks,
    db_session_factory = Depends(get_db_session_factory)
):
    hostnames = request.hostnames or None

    # Create job entry
    job_id = create_job(
        description=f"Device sync for {','.join(hostnames or []) or 'ALL'}",
        category="device_sync"
    )


    # Queue background task
    background.add_task(
        run_device_sync,
        job_id,
        hostnames,
        db_session_factory
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": "Device sync started"
    }


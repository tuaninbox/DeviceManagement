from fastapi import APIRouter, Depends, HTTPException
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func
from app.services.job_manager import create_job
from app.services.device_sync import run_device_sync
from app import models, schemas, crud, database
from core.load_inventory import collect_inventory
from app.normalizers.device_normalizer import (
    normalize_device,
    normalize_interfaces,
    normalize_modules,
    normalize_software_info,
)
from core.logging_manager import setup_loggers
from config.config_loader import load_device_management_config
from pathlib import Path

# Set up loggers
success_logger, fail_logger = setup_loggers(logger_name="app_router_devices")

router = APIRouter(prefix="/devices", tags=["devices"])

def get_db_session_factory():
    """
    Returns a callable that creates new DB sessions.
    Useful for background tasks where request-scoped DB sessions are closed.
    """
    return database.SessionLocal

# Dependency for DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.Device)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    success_logger.info(f"Creating device: {device.hostname}")
    return crud.create_device(db=db, device=device)

# @router.get("/", response_model=List[schemas.Device])
@router.get("/", response_model=schemas.DeviceListResponse)
def list_devices(page: int = 1,page_size: int = 100,db: Session = Depends(get_db)):
    success_logger.info(f"Listing devices page {page} with {page_size} devices")
    
    # Convert page → skip
    skip = (page - 1) * page_size

    # Query total count
    total = db.query(models.Device).count()

    # Query paginated items
    items = crud.get_devices(db, skip=skip, limit=page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.get("/all", response_model=List[schemas.Device])
def list_all_devices(db: Session = Depends(get_db)):
    success_logger.info("Listing ALL devices")
    return crud.get_all_devices(db)


@router.get("/{hostname}", response_model=schemas.Device)
def get_device_by_hostname(hostname: str, db: Session = Depends(get_db)):
    success_logger.info(f"Fetching device by hostname: {hostname}")
    device = (
        db.query(models.Device)
        .filter(func.lower(models.Device.hostname) == hostname.lower())
        .first()
    )

    if not device:
        fail_logger.warning(f"Device '{hostname}' not found")
        raise HTTPException(
            status_code=404,
            detail=f"Device '{hostname}' not found"
        )

    return device


@router.post("/sync")
def sync_devices(
    request: schemas.SyncRequest,
    background: BackgroundTasks,
    db_session_factory = Depends(get_db_session_factory)
):
    hostnames = request.hostnames or None

    # Create job entry
    job_id = create_job(
        description=f"Device sync for {hostnames or 'ALL'}",
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



# @router.post("/sync")
# def sync_devices(request: schemas.SyncRequest, db: Session = Depends(get_db)):
#     hostnames = request.hostnames

#     # If hostnames missing or empty → sync ALL devices
#     if not hostnames:
#         hostnames = None

#     success_logger.info(f"Starting sync for devices: {hostnames or 'ALL'}")

#     # Load folders from config
#     cfg = load_device_management_config()
#     config_folder = cfg["config_folder"]
#     operational_folder = cfg["operational_folder"]

#     updated_devices = []
#     errors = []

#     try:
#         raw_list = collect_inventory(hostnames=hostnames)
#     except Exception as e:
#         return {
#             "success": False,
#             "error": f"Failed to collect inventory: {e}"
#         }

#     for raw in raw_list:
#         hostname = raw["host_info"]["hostname"]
#         success_logger.info(f"Syncing device: {hostname}")

#         try:
#             # DEVICE METADATA
#             device_data = normalize_device(raw)
#             device_data["running_config_path"] = str(config_folder / hostname)
#             device_data["routing_table_path"] = str(operational_folder / hostname)
#             device_data["mac_table_path"] = str(operational_folder / hostname)

#             db_dev = crud.upsert_device(db, device_data)

#             # INTERFACES
#             iface_list = normalize_interfaces(raw)
#             crud.upsert_interfaces(db, db_dev.id, iface_list)

#             # MODULES
#             module_list = normalize_modules(raw)
#             crud.upsert_modules(db, db_dev.id, module_list)

#             # SOFTWARE
#             sw = normalize_software_info(raw)
#             crud.upsert_software_info(db, db_dev.id, sw)

#             updated_devices.append({
#                 "hostname": hostname,
#                 "device_id": db_dev.id,
#                 "updated": {
#                     "device": True,
#                     "interfaces": len(iface_list),
#                     "modules": len(module_list),
#                     "software": True
#                 }
#             })

#         except Exception as e:
#             errors.append({"hostname": hostname, "error": str(e)})

#     return {
#         "success": len(errors) == 0,
#         "updated_devices": updated_devices,
#         "errors": errors
#     }


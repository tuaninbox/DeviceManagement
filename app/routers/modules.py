from fastapi import APIRouter, Depends, HTTPException
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func
from app import models, schemas, crud, database
from app.services.job_manager import create_job
from app.services.module_eox_sync import run_module_eox_sync
from core.logging_manager import setup_loggers

router = APIRouter()
success_logger, fail_logger = setup_loggers(logger_name="app_router_modules")

router = APIRouter(prefix="/modules", tags=["modules"])

def get_db_session_factory():
    """
    Returns a callable that creates new DB sessions.
    Useful for background tasks where request-scoped DB sessions are closed.
    """
    return database.SessionLocal

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create a single module
@router.post("/", response_model=schemas.ModuleBase)
def create_module(module: schemas.ModuleBase, db: Session = Depends(get_db)):
    return crud.create_module(db=db, module=module)

# List all modules
@router.get("/", response_model=List[schemas.ModuleBase])
def list_modules(db: Session = Depends(get_db)):
    return crud.get_modules(db)

# Get module by serial number
@router.get("/{serial_number}", response_model=schemas.ModuleBase)
def get_module_by_serial(serial_number: str, db: Session = Depends(get_db)):
    module = (
        db.query(models.Module)
        .filter(func.lower(models.Module.serial_number) == serial_number.lower())
        .first()
    )
    if not module:
        raise HTTPException(
            status_code=404,
            detail=f"Module with serial '{serial_number}' not found"
        )
    return module



@router.post("/sync-eox")
def sync_modules_eox(
    request: schemas.SyncEoxRequest,
    background: BackgroundTasks,
    db_session_factory=Depends(get_db_session_factory),
    db: Session = Depends(get_db)
):
    """
    Launch background job to sync Cisco EoX coverage information for modules.
    """

    serials_to_sync = set()

    # Case 1: Modules page → explicit serial numbers
    if request.serial_numbers:
        normalized = {s.strip().upper() for s in request.serial_numbers}
        modules = (
            db.query(models.Module)
            .filter(models.Module.serial_number.in_(normalized))
            .all()
        )
        for m in modules:
            if m.serial_number:
                serials_to_sync.add(m.serial_number)

    # Case 2: Devices page → device IDs provided
    elif request.device_ids:
        modules = (
            db.query(models.Module)
            .filter(models.Module.device_id.in_(request.device_ids))
            .filter(models.Module.serial_number.isnot(None))
            .all()
        )
        for m in modules:
            serials_to_sync.add(m.serial_number)

    # Case 3: No serials and no device IDs → sync ALL modules
    else:
        modules = (
            db.query(models.Module)
            .filter(models.Module.serial_number.isnot(None))
            .all()
        )
        for m in modules:
            serials_to_sync.add(m.serial_number)

    serials = list(serials_to_sync)

    if not serials:
        return {
            "success": False,
            "message": "No serial numbers found",
        }

    # Create job
    job_id = create_job(
        description=f"EoX sync for {len(serials)} modules",
        category="module_eox_sync"
    )

    # Queue background worker
    background.add_task(
        run_module_eox_sync,
        job_id,
        serials,
        db_session_factory
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": f"EoX sync started for {len(serials)} modules"
    }


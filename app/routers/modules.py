from fastapi import APIRouter, Depends, HTTPException
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func
from datetime import datetime
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



# @router.post("/sync-eox")
# def sync_modules_eox(
#     request: schemas.SyncEoxRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     Sync Cisco EoX coverage information for modules.

#     Supports three workflows:
#     1. request.serial_numbers → sync only these serials (Modules page)
#     2. request.device_ids → sync modules belonging to these devices (Devices page)
#     3. neither provided → sync ALL modules with serial numbers
#     """
#     try:
#         serials_to_sync = set()

#         # ----------------------------------------------------
#         # Case 1: Modules page → explicit serial numbers
#         # ----------------------------------------------------
#         if request.serial_numbers:
#             normalized = {s.strip().upper() for s in request.serial_numbers}
#             modules = (
#                 db.query(models.Module)
#                 .filter(models.Module.serial_number.in_(normalized))
#                 .all()
#             )
#             for m in modules:
#                 if m.serial_number:
#                     serials_to_sync.add(m.serial_number)

#         # ----------------------------------------------------
#         # Case 2: Devices page → device IDs provided
#         # ----------------------------------------------------
#         elif request.device_ids:
#             modules = (
#                 db.query(models.Module)
#                 .filter(models.Module.device_id.in_(request.device_ids))
#                 .filter(models.Module.serial_number.isnot(None))
#                 .all()
#             )
#             for m in modules:
#                 serials_to_sync.add(m.serial_number)

#         # ----------------------------------------------------
#         # Case 3: No serials and no device IDs → sync ALL modules
#         # ----------------------------------------------------
#         else:
#             modules = (
#                 db.query(models.Module)
#                 .filter(models.Module.serial_number.isnot(None))
#                 .all()
#             )
#             for m in modules:
#                 serials_to_sync.add(m.serial_number)

#         # Convert to list
#         serials = list(serials_to_sync)

#         if not serials:
#             fail_logger.error("No serial numbers found for EoX sync")
#             return {
#                 "success": False,
#                 "updated_modules": [],
#                 "errors": [{"message": "No serial numbers found"}],
#             }

#         success_logger.info(f"Starting EoX sync for {len(serials)} serials")

#         # ----------------------------------------------------
#         # Step 2: Query Cisco EoX API
#         # ----------------------------------------------------
#         try:
#             eox_results = get_eox_data_from_sn(serials)
#         except Exception as e:
#             fail_logger.error(f"EoX API call failed: {e}")
#             return {
#                 "success": False,
#                 "updated_modules": [],
#                 "errors": [{"message": f"EoX API error: {e}"}],
#             }

#         serial_data_list = eox_results.get("serial_numbers", [])

#         # ----------------------------------------------------
#         # Step 3: Update DB modules
#         # ----------------------------------------------------
#         updated_modules = []
#         errors = []

#         # Re-query modules for update (ensures consistent list)
#         modules_for_update = (
#             db.query(models.Module)
#             .filter(models.Module.serial_number.in_(serials))
#             .all()
#         )

#         for m in modules_for_update:
#             try:
#                 match = next(
#                     (item for item in serial_data_list if item.get("sr_no") == m.serial_number),
#                     None
#                 )
#                 if not match:
#                     continue

#                 # Parse coverage end date
#                 date_str = match.get("coverage_end_date")
#                 if date_str:
#                     try:
#                         m.warranty_expiry = datetime.strptime(date_str, "%Y-%m-%d").date()
#                     except ValueError:
#                         m.warranty_expiry = None
#                 else:
#                     m.warranty_expiry = None

#                 m.under_warranty = match.get("is_covered") == "YES"
#                 m.eox_announced = match.get("end_of_sale_date")
#                 m.eox_eol = match.get("end_of_support_date")

#                 updated_modules.append({
#                     "module_id": m.id,
#                     "serial_number": m.serial_number,
#                     "updated": True,
#                 })

#             except Exception as e:
#                 errors.append({
#                     "module_id": m.id,
#                     "serial_number": m.serial_number,
#                     "error": str(e),
#                 })

#         db.commit()

#         success_logger.info(
#             f"EoX sync complete: {len(updated_modules)} updated, {len(errors)} errors"
#         )

#         return {
#             "success": len(errors) == 0,
#             "updated_modules": updated_modules,
#             "errors": errors,
#         }

#     except Exception as e:
#         db.rollback()
#         fail_logger.error(f"Failed to sync EoX data: {e}", exc_info=True)
#         return {
#             "success": False,
#             "updated_modules": [],
#             "errors": [{"message": str(e)}],
#         }


# @router.post("/sync-eox")
# def sync_modules_eox(
#     request: schemas.SyncEoxRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     Sync Cisco EoX coverage information for modules.
#     If serial_numbers is None or empty → sync ALL modules with serials.
#     """
#     try:
#         # -------------------------
#         # Step 1: Determine which serials to sync
#         # -------------------------
#         if request.serial_numbers:
#             # User provided a list → filter modules by these serials
#             normalized = {s.strip().upper() for s in request.serial_numbers}
#             modules = (
#                 db.query(models.Module)
#                 .filter(models.Module.serial_number.in_(normalized))
#                 .all()
#             )
#         else:
#             # No list provided → sync ALL modules with serial numbers
#             modules = (
#                 db.query(models.Module)
#                 .filter(models.Module.serial_number.isnot(None))
#                 .all()
#             )

#         serials = [m.serial_number for m in modules if m.serial_number]

#         if not serials:
#             fail_logger.error("No serial numbers found for EoX sync")
#             return {
#                 "success": False,
#                 "updated_modules": [],
#                 "errors": [{"message": "No serial numbers found"}],
#             }

#         success_logger.info(f"Starting EoX sync for {len(serials)} serials")

#         # -------------------------
#         # Step 2: Query Cisco EoX API
#         # -------------------------
#         try:
#             eox_results = get_eox_data_from_sn(serials)
#         except Exception as e:
#             fail_logger.error(f"EoX API call failed: {e}")
#             return {
#                 "success": False,
#                 "updated_modules": [],
#                 "errors": [{"message": f"EoX API error: {e}"}],
#             }

#         serial_data_list = eox_results.get("serial_numbers", [])

#         # -------------------------
#         # Step 3: Update DB modules
#         # -------------------------
#         updated_modules = []
#         errors = []

#         for m in modules:
#             try:
#                 match = next(
#                     (item for item in serial_data_list if item.get("sr_no") == m.serial_number),
#                     None
#                 )
#                 if not match:
#                     continue

#                 # Parse coverage end date
#                 date_str = match.get("coverage_end_date")
#                 if date_str:
#                     try:
#                         m.warranty_expiry = datetime.strptime(date_str, "%Y-%m-%d").date()
#                     except ValueError:
#                         m.warranty_expiry = None
#                 else:
#                     m.warranty_expiry = None

#                 m.under_warranty = match.get("is_covered") == "YES"
#                 m.eox_announced = match.get("end_of_sale_date")
#                 m.eox_eol = match.get("end_of_support_date")

#                 updated_modules.append({
#                     "module_id": m.id,
#                     "serial_number": m.serial_number,
#                     "updated": True,
#                 })

#             except Exception as e:
#                 errors.append({
#                     "module_id": m.id,
#                     "serial_number": m.serial_number,
#                     "error": str(e),
#                 })

#         db.commit()

#         success_logger.info(
#             f"EoX sync complete: {len(updated_modules)} updated, {len(errors)} errors"
#         )

#         return {
#             "success": len(errors) == 0,
#             "updated_modules": updated_modules,
#             "errors": errors,
#         }

#     except Exception as e:
#         db.rollback()
#         fail_logger.error(f"Failed to sync EoX data: {e}", exc_info=True)
#         return {
#             "success": False,
#             "updated_modules": [],
#             "errors": [{"message": str(e)}],
#         }

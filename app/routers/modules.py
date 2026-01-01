from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func
from datetime import datetime
from app import models, schemas, crud, database
from core.eox import get_eox_data_from_sn
from core.logging_manager import setup_loggers

router = APIRouter()
success_logger, fail_logger = setup_loggers(logger_name="app_router_modules")

router = APIRouter(prefix="/modules", tags=["modules"])

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
    db: Session = Depends(get_db)
):
    """
    Sync Cisco EoX coverage information for modules.
    If serial_numbers is None or empty → sync ALL modules with serials.
    """
    try:
        # -------------------------
        # Step 1: Determine which serials to sync
        # -------------------------
        if request.serial_numbers:
            # User provided a list → filter modules by these serials
            normalized = {s.strip().upper() for s in request.serial_numbers}
            modules = (
                db.query(models.Module)
                .filter(models.Module.serial_number.in_(normalized))
                .all()
            )
        else:
            # No list provided → sync ALL modules with serial numbers
            modules = (
                db.query(models.Module)
                .filter(models.Module.serial_number.isnot(None))
                .all()
            )

        serials = [m.serial_number for m in modules if m.serial_number]

        if not serials:
            fail_logger.error("No serial numbers found for EoX sync")
            return {
                "success": False,
                "updated_modules": [],
                "errors": [{"message": "No serial numbers found"}],
            }

        success_logger.info(f"Starting EoX sync for {len(serials)} serials")

        # -------------------------
        # Step 2: Query Cisco EoX API
        # -------------------------
        try:
            eox_results = get_eox_data_from_sn(serials)
        except Exception as e:
            fail_logger.error(f"EoX API call failed: {e}")
            return {
                "success": False,
                "updated_modules": [],
                "errors": [{"message": f"EoX API error: {e}"}],
            }

        serial_data_list = eox_results.get("serial_numbers", [])

        # -------------------------
        # Step 3: Update DB modules
        # -------------------------
        updated_modules = []
        errors = []

        for m in modules:
            try:
                match = next(
                    (item for item in serial_data_list if item.get("sr_no") == m.serial_number),
                    None
                )
                if not match:
                    continue

                # Parse coverage end date
                date_str = match.get("coverage_end_date")
                if date_str:
                    try:
                        m.warranty_expiry = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        m.warranty_expiry = None
                else:
                    m.warranty_expiry = None

                m.under_warranty = match.get("is_covered") == "YES"
                m.eox_announced = match.get("end_of_sale_date")
                m.eox_eol = match.get("end_of_support_date")

                updated_modules.append({
                    "module_id": m.id,
                    "serial_number": m.serial_number,
                    "updated": True,
                })

            except Exception as e:
                errors.append({
                    "module_id": m.id,
                    "serial_number": m.serial_number,
                    "error": str(e),
                })

        db.commit()

        success_logger.info(
            f"EoX sync complete: {len(updated_modules)} updated, {len(errors)} errors"
        )

        return {
            "success": len(errors) == 0,
            "updated_modules": updated_modules,
            "errors": errors,
        }

    except Exception as e:
        db.rollback()
        fail_logger.error(f"Failed to sync EoX data: {e}", exc_info=True)
        return {
            "success": False,
            "updated_modules": [],
            "errors": [{"message": str(e)}],
        }

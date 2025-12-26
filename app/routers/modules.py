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
def sync_modules_eox(db: Session = Depends(get_db)):
    """
    Sync Cisco EoX coverage information for all modules in DB.
    """
    try:
        # Step 1: collect all serials from modules
        modules = db.query(models.Module).filter(models.Module.serial_number.isnot(None)).all()
        serials = [m.serial_number for m in modules if m.serial_number]

        if not serials:
            fail_logger.error("No serial numbers found in modules table")
            return {"status": "no_serials"}

        # Step 2: query Cisco EoX API
        eox_results = get_eox_data_from_sn(serials)
        print(eox_results)

        # Step 3: update modules with coverage info
        updated_count = 0
        serial_data_list = eox_results.get("serial_numbers", [])

        for m in modules:
            # find the matching entry in the combined list
            match = next((item for item in serial_data_list if item.get("sr_no") == m.serial_number), None)
            if not match:
                continue

            # Convert coverage_end_date string to Python date
            date_str = match.get("coverage_end_date")
            if date_str:
                try:
                    m.warranty_expiry = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    m.warranty_expiry = None
            else:
                m.warranty_expiry = None
            m.under_warranty = match.get("is_covered") == "YES"
            # If your API response includes these fields, map them; otherwise leave None
            m.eox_announced = match.get("end_of_sale_date")
            m.eox_eol = match.get("end_of_support_date")

            updated_count += 1

        db.commit()
        success_logger.info(f"Updated {updated_count} modules with Cisco EoX coverage info")
        return {"status": "success", "updated": updated_count}

    except Exception as e:
        db.rollback()
        fail_logger.error(f"Failed to sync EoX data: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func

from app import models, schemas, crud, database

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

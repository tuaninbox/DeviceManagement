from app import models, schemas
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import database

router = APIRouter(prefix="/modules", tags=["modules"])

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/device/{device_id}", response_model=schemas.Module)
def add_module(device_id: int, module: schemas.ModuleCreate, db: Session = Depends(get_db)):
    db_device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    db_module = models.Module(device_id=device_id, **module.dict())
    db.add(db_module)
    db.commit()
    db.refresh(db_module)
    return db_module

@router.get("/device/{device_id}", response_model=List[schemas.Module])
def list_modules(device_id: int, db: Session = Depends(get_db)):
    return db.query(models.Module).filter(models.Module.device_id == device_id).all()

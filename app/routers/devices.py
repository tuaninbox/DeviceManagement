from app import schemas
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, database
from load_inventory import collect_inventory  # your script
from app.normalizers.device_normalizer import (
    normalize_device,
    normalize_interfaces,
    normalize_modules,
    normalize_mac_table,
    normalize_routing_table,
    normalize_running_config,
    normalize_software_info
)



router = APIRouter(prefix="/devices", tags=["devices"])

# Create SQLAlchemy Session, yield to endpoint and ensure session closes
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.Device)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    return crud.create_device(db=db, device=device)

# run dependency get_db
# Takes the list of ORM objects returned by get_devices
# Converts each ORM object into a Pydantic schemas.Device
# Serializes the list into JSON
# Sends it back to the client
@router.get("/", response_model=List[schemas.Device])
def list_devices(db: Session = Depends(get_db)):
    return crud.get_devices(db)

@router.get("/{device_id}", response_model=schemas.Device)
def get_device(device_id: int, db: Session = Depends(get_db)):
    db_device = crud.get_device(db, device_id=device_id)
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    return db_device

@router.post("/sync")
def sync_devices(db: Session = Depends(get_db)):
    raw_inventory = collect_inventory()
    updated_devices = []

    for raw in raw_inventory:
        hostname = raw["host_info"]["hostname"]

        try:
            # DEVICE
            device_data = normalize_device(raw)
            db_dev = crud.upsert_device(db, device_data)

            # INTERFACES
            iface_list = normalize_interfaces(raw)
            crud.upsert_interfaces(db, db_dev.id, iface_list)

            # MODULES
            module_list = normalize_modules(raw)
            crud.upsert_modules(db, db_dev.id, module_list)

            # SOFTWARE INFO
            sw = normalize_software_info(raw)
            crud.upsert_software_info(db, db_dev.id, sw)

            # RUNNING CONFIG (file reference)
            cfg = normalize_running_config(raw)
            if cfg:
                crud.upsert_running_config(db, db_dev.id, hostname, cfg)

            # ROUTING TABLE (file reference)
            routes = normalize_routing_table(raw)
            if routes:
                crud.upsert_routing_table(db, db_dev.id, hostname, routes)

            # MAC TABLE (file reference)
            mac = normalize_mac_table(raw)
            if mac:
                crud.upsert_mac_table(db, db_dev.id, hostname, mac)

            updated_devices.append(db_dev)

        except Exception as e:
            print(f"[ERROR] Failed to sync device {hostname}: {e}")

    return updated_devices



from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func

from app import models, schemas, crud, database
from load_inventory import collect_inventory
from app.normalizers.device_normalizer import (
    normalize_device,
    normalize_interfaces,
    normalize_modules,
    normalize_mac_table,
    normalize_routing_table,
    normalize_running_config,
    normalize_software_info,
)
from core.logging_manager import setup_loggers

# Set up loggers
success_logger, fail_logger = setup_loggers(logger_name="app_router_devices")

router = APIRouter(prefix="/devices", tags=["devices"])

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

@router.get("/", response_model=List[schemas.Device])
def list_devices(db: Session = Depends(get_db)):
    success_logger.info("Listing all devices")
    return crud.get_devices(db)

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
def sync_devices(db: Session = Depends(get_db)):
    success_logger.info("Starting device sync from inventory")
    raw_inventory = collect_inventory()
    updated_devices = []

    for raw in raw_inventory:
        hostname = raw["host_info"]["hostname"]
        success_logger.info(f"Syncing device: {hostname}")

        try:
            # DEVICE
            device_data = normalize_device(raw)
            db_dev = crud.upsert_device(db, device_data)
            success_logger.info(f"Upserted device: {hostname}")

            # INTERFACES
            iface_list = normalize_interfaces(raw)
            crud.upsert_interfaces(db, db_dev.id, iface_list)
            success_logger.info(f"Upserted {len(iface_list)} interfaces for {hostname}")

            # MODULES
            module_list = normalize_modules(raw)
            crud.upsert_modules(db, db_dev.id, module_list)
            success_logger.info(f"Upserted {len(module_list)} modules for {hostname}")

            # SOFTWARE INFO
            sw = normalize_software_info(raw)
            crud.upsert_software_info(db, db_dev.id, sw)
            success_logger.info(f"Upserted software info for {hostname}")

            # RUNNING CONFIG
            cfg = normalize_running_config(raw)
            if cfg:
                crud.upsert_running_config(db, db_dev.id, hostname, cfg)
                success_logger.info(f"Upserted running config for {hostname}")

            # ROUTING TABLE
            routes = normalize_routing_table(raw)
            if routes:
                crud.upsert_routing_table(db, db_dev.id, hostname, routes)
                success_logger.info(f"Upserted routing table for {hostname}")

            # MAC TABLE
            mac = normalize_mac_table(raw)
            if mac:
                crud.upsert_mac_table(db, db_dev.id, hostname, mac)
                success_logger.info(f"Upserted MAC table for {hostname}")

            updated_devices.append(db_dev)

        except Exception as e:
            fail_logger.error(f"Failed to sync device {hostname}: {e}", exc_info=True)

    success_logger.info(f"Device sync completed. {len(updated_devices)} devices updated.")
    return updated_devices

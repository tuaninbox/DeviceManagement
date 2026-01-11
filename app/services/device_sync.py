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
from app.services.job_manager import update_job
from pathlib import Path

# Set up loggers
success_logger, fail_logger = setup_loggers(logger_name="app_services_device_sync")

from datetime import datetime
from app.services.job_manager import update_job
from core.load_inventory import collect_inventory
from app.normalizers.device_normalizer import (
    normalize_device,
    normalize_interfaces,
    normalize_modules,
    normalize_software_info,
)
import app.crud as crud


def run_device_sync(job_id, hostnames, db_session_factory):
    """
    Background worker that performs full device inventory sync.
    Updates job status throughout the lifecycle.
    """
    update_job(job_id, status="running", started_at=datetime.utcnow())

    db = db_session_factory()

    try:
        success_logger.info(f"[JOB {job_id}] Starting background sync for: {hostnames or 'ALL'}")

        # Load folders from config
        cfg = load_device_management_config()
        config_folder = cfg["config_folder"]
        operational_folder = cfg["operational_folder"]

        updated_devices = []
        errors = []

        # ----------------------------------------------------
        # Step 1: Collect inventory from devices
        # ----------------------------------------------------
        try:
            raw_list = collect_inventory(hostnames=hostnames)
        except Exception as e:
            msg = f"Failed to collect inventory: {e}"
            fail_logger.error(f"[JOB {job_id}] {msg}")
            update_job(job_id, status="failed", finished_at=datetime.utcnow(), error=msg)
            return

        # ----------------------------------------------------
        # Step 2: Process each device
        # ----------------------------------------------------
        for raw in raw_list:
            hostname = raw["host_info"]["hostname"]
            success_logger.info(f"[JOB {job_id}] Syncing device: {hostname}")

            try:
                # DEVICE METADATA
                device_data = normalize_device(raw)
                device_data["running_config_path"] = str(config_folder / hostname)
                device_data["routing_table_path"] = str(operational_folder / hostname)
                device_data["mac_table_path"] = str(operational_folder / hostname)

                db_dev = crud.upsert_device(db, device_data)

                # INTERFACES
                iface_list = normalize_interfaces(raw)
                crud.upsert_interfaces(db, db_dev.id, iface_list)

                # MODULES
                module_list = normalize_modules(raw)
                crud.upsert_modules(db, db_dev.id, module_list)

                # SOFTWARE
                sw = normalize_software_info(raw)
                crud.upsert_software_info(db, db_dev.id, sw)

                updated_devices.append({
                    "hostname": hostname,
                    "device_id": db_dev.id,
                    "updated": {
                        "device": True,
                        "interfaces": len(iface_list),
                        "modules": len(module_list),
                        "software": True
                    }
                })

            except Exception as e:
                err_msg = str(e)
                errors.append({"hostname": hostname, "error": err_msg})
                fail_logger.error(f"[JOB {job_id}] Error syncing {hostname}: {err_msg}")

        db.commit()

        # ----------------------------------------------------
        # Step 3: Finalize job
        # ----------------------------------------------------
        success_logger.info(
            f"[JOB {job_id}] Background sync complete: {len(updated_devices)} updated, {len(errors)} errors"
        )

        update_job(
            job_id,
            status="completed",
            finished_at=datetime.utcnow(),
            result={
                "updated_devices": updated_devices,
                "errors": errors,
            }
        )

    except Exception as e:
        msg = f"Background sync failed: {e}"
        fail_logger.error(f"[JOB {job_id}] {msg}", exc_info=True)

        update_job(
            job_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error=msg
        )

    finally:
        db.close()

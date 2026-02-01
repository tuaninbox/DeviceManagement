# from app.databases import devices
# from app.models import devices
# from app.schemas import devices
from core.load_device import sync_device_details
from app.normalizers.device_normalizer import (
    normalize_device,
    normalize_interfaces,
    normalize_modules,
    normalize_software_info,
)
from config.config_loader import load_device_management_config
from pathlib import Path
from datetime import datetime, timezone
import app.crud as crud
from app.services.job_manager import update_job
# from app.databases.devices import SessionLocal
from core.logging_manager import setup_loggers
from inventory.load_inventory import load_inventory
from core.utility.utility import extract_hostname

success_logger, fail_logger = setup_loggers(logger_name="app_services_inventory_load")

def load_inventory_to_db(job_id, db_session_factory):
    """
    Load static or dynamic inventory into the database using load_inventory().
    If device exists, update IP, OS, vendor, type.
    If new, insert it.
    """

    update_job(job_id, status="running", started_at=datetime.now(timezone.utc))

    db = db_session_factory()
    updated = []
    errors = []

    try:
        # ------------------------------------------------------------
        # Step 1: Load inventory from provider (static or dynamic)
        # ------------------------------------------------------------
        try:
            inventory_rows = load_inventory()   # <-- use your existing function
        except Exception as e:
            msg = f"Failed to load inventory: {e}"
            fail_logger.error(msg)
            update_job(job_id, status="failed", finished_at=datetime.now(timezone.utc), error=msg)
            return

        # ------------------------------------------------------------
        # Step 2: Insert/update devices in DB
        # ------------------------------------------------------------
        for row in inventory_rows:
            try:
                hostname = row["hostname"]
                mgmt_ip = row["mgmt_address"]

                device_data = {
                    "hostname": hostname,
                    "mgmt_address": mgmt_ip,
                    "port": row.get("port"),
                    "os": row.get("os") or "unknown",
                    "vendor": row.get("vendor"),
                    "type": row.get("type"),
                    "location": row.get("location"),
                    "device_group": row.get("device_group"),
                    "last_updated": datetime.now(timezone.utc),
                }

                db_dev = crud.upsert_device(db, device_data)

                updated.append({
                    "hostname": hostname,
                    "device_id": db_dev.id,
                    "updated": True
                })

            except Exception as e:
                errors.append({"hostname": row.get("hostname"), "error": str(e)})
                fail_logger.error(f"Error importing {row.get('hostname')}: {e}")

        db.commit()

        # ------------------------------------------------------------
        # Step 3: Finalize job
        # ------------------------------------------------------------
        update_job(
            job_id,
            status="completed",
            finished_at=datetime.now(timezone.utc),
            result={"updated": updated, "errors": errors}
        )

    except Exception as e:
        msg = f"Inventory load failed: {e}"
        fail_logger.error(msg, exc_info=True)
        update_job(job_id, status="failed", finished_at=datetime.now(timezone.utc), error=msg)

    finally:
        db.close()



def run_device_sync(job_id, hostnames, db_session_factory):
    """
    Background worker that performs device sync.
    Reads devices FROM DATABASE (not from inventory),
    connects to each device, collects details, and updates DB.
    """

    update_job(job_id, status="running", started_at=datetime.now(timezone.utc))
    db = db_session_factory()

    try:
        success_logger.info(f"[JOB {job_id}] Starting device sync for: {hostnames or 'ALL'}")

        # ----------------------------------------------------
        # Step 1: Load devices from DB
        # ----------------------------------------------------
        if hostnames:
            db_devices = crud.get_device(db, hostnames)
        else:
            db_devices = crud.get_all_devices(db)

        if not db_devices:
            msg = "No devices found in database to sync"
            fail_logger.error(f"[JOB {job_id}] {msg}")
            update_job(job_id, status="failed", finished_at=datetime.now(timezone.utc), error=msg)
            return

        # Convert DB rows into the format sync_device_details expects
        device_list = []
        for dev in db_devices:
            device_list.append({
                "Host": dev.hostname,
                "IP": dev.mgmt_address,
                "OS": dev.os or "unknown",
                "Port": dev.port or 22,
                "Location": dev.location,
                "Group": dev.device_group,
            })

        # ----------------------------------------------------
        # Step 2: Run SSH sessions to collect device details
        # ----------------------------------------------------
        try:
            raw_list = sync_device_details(hostnames=device_list)
        except Exception as e:
            msg = f"Failed to sync devices: {e}"
            fail_logger.error(f"[JOB {job_id}] {msg}")
            update_job(job_id, status="failed", finished_at=datetime.now(timezone.utc), error=msg)
            return

        # Load folders from config
        cfg = load_device_management_config()
        config_folder = Path(cfg["config_folder"])
        operational_folder = Path(cfg["operational_folder"])

        updated_devices = []
        errors = []

        # ----------------------------------------------------
        # Step 3: Process each device result
        # ----------------------------------------------------
        for raw in raw_list:
            
            hostname = extract_hostname(raw)
            success_logger.info(f"[JOB {job_id}] Syncing device: {hostname}")

            try:
                # DEVICE METADATA
                device_data = normalize_device(raw)
                if not device_data:
                    raise ValueError("normalize_device returned None")

                device_data["running_config_path"] = str((config_folder / hostname.lower()).expanduser())
                device_data["routing_table_path"] = str((operational_folder / hostname.lower()).expanduser())
                device_data["mac_table_path"] = str((operational_folder / hostname.lower()).expanduser())

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
        # Step 4: Finalize job
        # ----------------------------------------------------
        success_logger.info(
            f"[JOB {job_id}] Device sync complete: {len(updated_devices)} updated, {len(errors)} errors"
        )

        update_job(
            job_id,
            status="completed",
            finished_at=datetime.now(timezone.utc),
            result={
                "updated_devices": updated_devices,
                "errors": errors,
            }
        )

    except Exception as e:
        msg = f"Device sync failed: {e}"
        fail_logger.error(f"[JOB {job_id}] {msg}", exc_info=True)

        update_job(
            job_id,
            status="failed",
            finished_at=datetime.now(timezone.utc),
            error=msg
        )

    finally:
        db.close()


# def run_device_sync_old(job_id, hostnames, db_session_factory):
#     """
#     Background worker that performs full device inventory sync.
#     Updates job status throughout the lifecycle.
#     """
#     update_job(job_id, status="running", started_at=datetime.now(timezone.utc))

#     db = db_session_factory()

#     try:
#         success_logger.info(f"[JOB {job_id}] Starting background sync for: {hostnames or 'ALL'}")

#         # Load folders from config
#         cfg = load_device_management_config()
#         config_folder = Path(cfg["config_folder"])
#         operational_folder = Path(cfg["operational_folder"])
#         updated_devices = []
#         errors = []

#         # ----------------------------------------------------
#         # Step 1: Collect inventory from devices
#         # ----------------------------------------------------
#         try:
#             raw_list = sync_device_details(hostnames=hostnames)
#         except Exception as e:
#             msg = f"Failed to collect inventory: {e}"
#             fail_logger.error(f"[JOB {job_id}] {msg}")
#             update_job(job_id, status="failed", finished_at=datetime.now(timezone.utc), error=msg)
#             return

#         # ----------------------------------------------------
#         # Step 2: Process each device
#         # ----------------------------------------------------
#         for raw in raw_list:
#             hostname = raw["host_info"]["hostname"]
#             success_logger.info(f"[JOB {job_id}] Syncing device: {hostname}")

#             try:
#                 # DEVICE METADATA
#                 device_data = normalize_device(raw)
#                 device_data["running_config_path"] = str((config_folder/ hostname.lower()).expanduser())
#                 device_data["routing_table_path"] = str((operational_folder/ hostname.lower()).expanduser())
#                 device_data["mac_table_path"] = str((operational_folder/ hostname.lower()).expanduser())

#                 db_dev = crud.upsert_device(db, device_data)

#                 # INTERFACES
#                 iface_list = normalize_interfaces(raw)
#                 crud.upsert_interfaces(db, db_dev.id, iface_list)

#                 # MODULES
#                 module_list = normalize_modules(raw)
#                 crud.upsert_modules(db, db_dev.id, module_list)

#                 # SOFTWARE
#                 sw = normalize_software_info(raw)
#                 crud.upsert_software_info(db, db_dev.id, sw)

#                 updated_devices.append({
#                     "hostname": hostname,
#                     "device_id": db_dev.id,
#                     "updated": {
#                         "device": True,
#                         "interfaces": len(iface_list),
#                         "modules": len(module_list),
#                         "software": True
#                     }
#                 })

#             except Exception as e:
#                 err_msg = str(e)
#                 errors.append({"hostname": hostname, "error": err_msg})
#                 fail_logger.error(f"[JOB {job_id}] Error syncing {hostname}: {err_msg}")

#         db.commit()

#         # ----------------------------------------------------
#         # Step 3: Finalize job
#         # ----------------------------------------------------
#         success_logger.info(
#             f"[JOB {job_id}] Background sync complete: {len(updated_devices)} updated, {len(errors)} errors"
#         )

#         update_job(
#             job_id,
#             status="completed",
#             finished_at=datetime.now(timezone.utc),
#             result={
#                 "updated_devices": updated_devices,
#                 "errors": errors,
#             }
#         )

#     except Exception as e:
#         msg = f"Background sync failed: {e}"
#         fail_logger.error(f"[JOB {job_id}] {msg}", exc_info=True)

#         update_job(
#             job_id,
#             status="failed",
#             finished_at=datetime.now(timezone.utc),
#             error=msg
#         )

#     finally:
#         db.close()

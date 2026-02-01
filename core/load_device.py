from core.credentials import get_credentials
from core.executor import run_parallel
from core.logging_manager import setup_loggers
from app.databases.devices import SessionLocal
from app.models.devices import Device
from sqlalchemy import func
import json
import datetime
from typing import List, Optional

success_logger, fail_logger = setup_loggers(logger_name="core_load_inventory")

def normalize_hostnames(hostnames):
    normalized = set()

    for h in hostnames:
        # Case 1: raw string
        if isinstance(h, str):
            normalized.add(h.strip().lower())
            continue

        # Case 2: dict with any hostname key
        if isinstance(h, dict):
            # Try common key variants
            for key in ("hostname", "Host", "HOST", "host"):
                if key in h and isinstance(h[key], str):
                    normalized.add(h[key].strip().lower())
                    break
            else:
                raise ValueError(f"Invalid hostname entry (dict missing hostname key): {h}")
            continue

        # Case 3: SQLAlchemy Device object
        if hasattr(h, "hostname") and isinstance(h.hostname, str):
            normalized.add(h.hostname.strip().lower())
            continue

        # Case 4: unsupported type
        raise ValueError(f"Invalid hostname entry: {h}")

    return normalized


def sync_device_details(
    hostnames: Optional[List[str]] = None
):
    """
    Load devices FROM DATABASE (not from inventory),
    optionally filter by hostnames, run parallel collector, and return results.
    """

    username, password = get_credentials()
    db = SessionLocal()

    try:
        # ------------------------------------------------------------
        # Step 1: Load devices from DB
        # ------------------------------------------------------------
        if hostnames:
            normalized = normalize_hostnames(hostnames)
            db_devices = (
                db.query(Device)
                .filter(func.lower(Device.hostname).in_(normalized))
                .all()
            )

            if not db_devices:
                msg = f"No matching hostnames found in database: {hostnames}"
                fail_logger.error(msg)
                raise ValueError(msg)

        else:
            db_devices = db.query(Device).all()

        if not db_devices:
            msg = "No devices found in database to sync"
            fail_logger.error(msg)
            raise RuntimeError(msg)

        # ------------------------------------------------------------
        # Step 2: Convert DB rows into run_parallel input format
        # ------------------------------------------------------------
        inventory_rows = []
        for dev in db_devices:
            inventory_rows.append({
                "Host": dev.hostname,
                "IP": dev.mgmt_address,
                "OS": dev.os or "unknown",
                "Port": dev.port or 22,
                "Location": dev.location,
                "Group": dev.device_group,
            })

        # ------------------------------------------------------------
        # Step 3: Run parallel executor (inventory collector mode)
        # ------------------------------------------------------------
        cmds = []  # no commands for inventory mode

        results = run_parallel(
            inventory_rows,
            cmds,
            username,
            password,
            collector_type="inventory",
        )

        return results

    except Exception as e:
        fail_logger.exception("sync_device_details failed")
        raise RuntimeError(f"{datetime.datetime.now()}: sync_device_details failed: {e}")

    finally:
        db.close()


# ------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------
def main():
    results = sync_device_details()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

# from inventory.inventory_factory import get_inventory_provider
# from core.credentials import get_credentials
# from core.executor import run_parallel

# import json
# import datetime
# from typing import List, Optional
# from core.logging_manager import setup_loggers
# from app.databases.devices import SessionLocal
# from app.models.devices import Device

# success_logger, fail_logger = setup_loggers(logger_name="core_load_inventory")

# def sync_device_details(
#     hostnames: Optional[List[str]] = None
# ):
#     """
#     Load inventory using the configured provider (static or dynamic),
#     optionally filter by hostnames, run parallel collector, and return results.
#     """

#     username, password = get_credentials()

#     # Load inventory from provider (static CSV or dynamic DB)
#     try:
#         provider = get_inventory_provider()
#         inventory_rows = provider.load()
#     except Exception as e:
#         fail_logger.exception("Failed to load inventory from provider")
#         raise RuntimeError(f"{datetime.datetime.now()}: Failed to load inventory: {e}")

#     # Optional filtering by list of hostnames
#     try:
#         if hostnames:
#             normalized = {h.strip().lower() for h in hostnames}

#             filtered = [
#                 row for row in inventory_rows
#                 if row.get("Host", "").strip().lower() in normalized
#             ]

#             if not filtered:
#                 msg = f"No matching hostnames found in inventory: {hostnames}"
#                 fail_logger.error(msg)
#                 raise ValueError(msg)

#             inventory_rows = filtered
#         # After: inventory_rows = filtered

#         db = SessionLocal()

#         for row in inventory_rows:
#             if not row.get("OS"):
#                 device = db.query(Device).filter(Device.hostname == row["Host"]).first()
#                 if device and device.os:
#                     row["OS"] = device.os

#         db.close()

#     except Exception:
#         fail_logger.exception("Inventory filtering failed")
#         raise

#     # Commands list (empty for inventory mode)
#     cmds = []

#     # Run parallel executor
#     results = run_parallel(
#         inventory_rows,
#         cmds,
#         username,
#         password,
#         collector_type="inventory",
#     )

#     return results


# # ------------------------------------------------------------
# # ✅ CLI entry point (still works as a standalone script)
# # ------------------------------------------------------------
# def main():
#     results = sync_device_details()
#     print(json.dumps(results, indent=2))


# if __name__ == "__main__":
#     main()

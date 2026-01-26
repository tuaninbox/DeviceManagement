from inventory.inventory_factory import get_inventory_provider
from core.credentials import get_credentials
from core.executor import run_parallel

import json
import datetime
from typing import List, Optional
from core.logging_manager import setup_loggers
from app.databases.devices import SessionLocal
from app.models.devices import Device

success_logger, fail_logger = setup_loggers(logger_name="core_load_inventory")

def sync_device_details(
    hostnames: Optional[List[str]] = None
):
    """
    Load inventory using the configured provider (static or dynamic),
    optionally filter by hostnames, run parallel collector, and return results.
    """

    username, password = get_credentials()

    # Load inventory from provider (static CSV or dynamic DB)
    try:
        provider = get_inventory_provider()
        inventory_rows = provider.load()
    except Exception as e:
        fail_logger.exception("Failed to load inventory from provider")
        raise RuntimeError(f"{datetime.datetime.now()}: Failed to load inventory: {e}")

    # Optional filtering by list of hostnames
    try:
        if hostnames:
            normalized = {h.strip().lower() for h in hostnames}

            filtered = [
                row for row in inventory_rows
                if row.get("Host", "").strip().lower() in normalized
            ]

            if not filtered:
                msg = f"No matching hostnames found in inventory: {hostnames}"
                fail_logger.error(msg)
                raise ValueError(msg)

            inventory_rows = filtered
        # After: inventory_rows = filtered

        db = SessionLocal()

        for row in inventory_rows:
            if not row.get("OS"):
                device = db.query(Device).filter(Device.hostname == row["Host"]).first()
                if device and device.os:
                    row["OS"] = device.os

        db.close()

    except Exception:
        fail_logger.exception("Inventory filtering failed")
        raise

    # Commands list (empty for inventory mode)
    cmds = []

    # Run parallel executor
    results = run_parallel(
        inventory_rows,
        cmds,
        username,
        password,
        collector_type="inventory",
    )

    return results


# ------------------------------------------------------------
# ✅ CLI entry point (still works as a standalone script)
# ------------------------------------------------------------
def main():
    results = sync_device_details()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

from inventory.inventory_factory import get_inventory_provider

import json
from datetime import datetime, timezone
from typing import List, Optional
from core.logging_manager import setup_loggers
from app.databases.devices import SessionLocal
from app.models.devices import Device

success_logger, fail_logger = setup_loggers(logger_name="core_load_inventory")

def load_inventory():
    """
    Load inventory using the configured provider (static or dynamic),
    optionally filter by hostnames, run parallel collector, and return results.
    """

    # Load inventory from provider (static CSV or dynamic DB)
    try:
        provider = get_inventory_provider()
        devices = provider.load()
    except Exception as e:
        fail_logger.exception("Failed to load inventory from provider")
        raise RuntimeError(f"{datetime.datetime.now()}: Failed to load inventory: {e}")

    print(f"Devices: {devices}")
    # Optional filtering by list of hostnames
    try:
        normalized = []
        for dev in devices:
            normalized.append({
                "hostname": dev["Host"],
                "mgmt_address": dev["IP"],
                "port": dev.get("Port") or 22,
                "location": dev.get("Location"),
                "device_group": dev.get("Group"),
                "os": dev.get("OS") or "unknown",
                "vendor": None,
                "type": None,
                "model": None,
                "serial_number": None,
                "uptime": None,
                "last_updated": datetime.now(timezone.utc),
            })

        db = SessionLocal()
        for entry in normalized:
            existing = db.query(Device).filter(Device.hostname == entry["hostname"]).first()
            if existing:
                for k, v in entry.items():
                    setattr(existing, k, v)
            else:
                db.add(Device(**entry))

        db.commit()
        db.close()

    except Exception:
        fail_logger.exception("Inventory filtering failed")
        raise

    # Commands list (empty for inventory mode)


    return normalized



    



# ------------------------------------------------------------
# ✅ CLI entry point (still works as a standalone script)
# ------------------------------------------------------------
def main():
    results = load_inventory()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

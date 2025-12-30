"""
Name: Get and Find Modules from Cisco IOS Devices
Author: Tuan Hoang
Version: 2.0 (refactored for FastAPI integration)
"""

import warnings
warnings.filterwarnings("ignore")

import csv
import json
import datetime

from core.credentials import get_credentials
from core.device.inventory import DeviceInventoryCollector   # import your collector class

# ------------------------------------------------------------
# ✅ Reusable function: FastAPI can call THIS
# ------------------------------------------------------------
def collect_modules(listfile: str = "inventory/devices.csv"):
    """
    Load inventory from CSV, run get_modules for each device, and return results.
    """

    # Load credentials
    username, password = get_credentials()

    # Load CSV inventory
    try:
        with open(listfile, "rt") as srcfile:
            reader = csv.DictReader(srcfile)
            inventory_rows = list(reader)
    except Exception as e:
        raise RuntimeError(f"{datetime.datetime.now()}: Failed to load inventory: {e}")

    results = []
    for row in inventory_rows:
        hostname = row.get("Host")
        os_type = row.get("OS")
        host = row.get("IP")

        # Initialize collector for this device
        collector = DeviceInventoryCollector(
            hostname=hostname,
            host=host,
            os=os_type,
            user=username,
            password=password,
            cmdlist=[]
        )

        modules = collector.get_modules()
        results.append({
            "hostname": hostname,
            "os": os_type,
            "modules": modules
        })

    return results


# ------------------------------------------------------------
# ✅ CLI entry point
# ------------------------------------------------------------
def main():
    results = collect_modules()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

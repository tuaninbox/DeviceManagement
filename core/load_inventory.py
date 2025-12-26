"""
Name: Get and Find Configuration from Cisco IOS Devices
Author: Tuan Hoang
Version: 2.0 (refactored for FastAPI integration)
"""

import warnings
warnings.filterwarnings("ignore")

import csv
import json
import datetime

from credentials import get_credentials
from executor import run_parallel


# ------------------------------------------------------------
# ✅ Reusable function: FastAPI will call THIS
# ------------------------------------------------------------
def collect_inventory(listfile: str = "inventory/devices.csv"):
    """
    Load inventory from CSV, run parallel collector, and return results.
    This function is safe to import and call from FastAPI.
    """

    # Load credentials (your existing logic)
    username, password = get_credentials()

    # Load CSV inventory
    try:
        with open(listfile, "rt") as srcfile:
            reader = csv.DictReader(srcfile)
            inventory_rows = list(reader)
            # print(inventory_rows)
    except Exception as e:
        raise RuntimeError(f"{datetime.datetime.now()}: Failed to load inventory: {e}")

    # Commands list (empty for inventory mode)
    cmds = []

    # Run your parallel executor
    results = run_parallel(
        inventory_rows,
        cmds,
        username,
        password,
        collector_type="inventory",
    )
    # print(results)
    return results


# ------------------------------------------------------------
# ✅ CLI entry point (still works as a standalone script)
# ------------------------------------------------------------
def main():
    results = collect_inventory()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

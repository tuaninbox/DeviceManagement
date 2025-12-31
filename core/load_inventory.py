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
def collect_inventory(
    listfile: str = "inventory/devices.csv",
    hostnames: list[str] | None = None
):
    """
    Load inventory from CSV, optionally filter by a list of hostnames,
    run parallel collector, and return results.
    """

    username, password = get_credentials()

    # Load CSV inventory
    try:
        with open(listfile, "rt") as srcfile:
            reader = csv.DictReader(srcfile)
            inventory_rows = list(reader)
    except Exception as e:
        raise RuntimeError(f"{datetime.datetime.now()}: Failed to load inventory: {e}")

    # Optional filtering by list of hostnames
    if hostnames:
        # Normalize hostnames (strip whitespace, lowercase)
        normalized = {h.strip().lower() for h in hostnames}

        filtered = [
            row for row in inventory_rows
            if row["hostname"].strip().lower() in normalized
        ]

        if not filtered:
            raise ValueError(f"No matching hostnames found in inventory: {hostnames}")

        inventory_rows = filtered

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
    results = collect_inventory()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

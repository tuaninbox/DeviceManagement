# app/normalizers/device_normalizer.py
from typing import List, Dict, Any
from datetime import datetime
import re
from core.logging_manager import setup_loggers

success_logger, fail_logger = setup_loggers(logger_name="app_normalizers")

# ------------------------------------------------------------
# ✅ Convert uptime string → integer seconds
# Example: "5 weeks, 1 day, 10 hours, 50 minutes"
# ------------------------------------------------------------
def parse_uptime(uptime_str: str) -> int:
    if not uptime_str:
        return None

    pattern = r"(\d+)\s+(week|day|hour|minute|second)s?"
    matches = re.findall(pattern, uptime_str)

    total_seconds = 0
    for value, unit in matches:
        value = int(value)
        if unit == "week":
            total_seconds += value * 7 * 24 * 3600
        elif unit == "day":
            total_seconds += value * 24 * 3600
        elif unit == "hour":
            total_seconds += value * 3600
        elif unit == "minute":
            total_seconds += value * 60
        elif unit == "second":
            total_seconds += value

    return total_seconds


# ------------------------------------------------------------
# ✅ Normalize Device (host_info → Device table)
# ------------------------------------------------------------
def normalize_device(raw: dict) -> dict:
    host = raw["host_info"]

    return {
        "hostname": host["hostname"],
        "mgmt_address": host["ip"],
        "uptime": parse_uptime(host.get("uptime")),
        "model": host.get("model"),
        "serial_number": host.get("serial"),
        "device_group": None,
        "location": None,
        "vrf": None,
    }


# ------------------------------------------------------------
# ✅ Normalize Interfaces (raw → Interface table)
# ------------------------------------------------------------
def normalize_interfaces(raw: dict) -> list:
    interfaces = raw.get("interfaces", [])

    normalized = []
    for iface in interfaces:
        normalized.append({
            "name": iface["name"],
            "status": iface.get("status"),
            "description": None,
            "vrf": None,
        })

    return normalized


# ------------------------------------------------------------
# ✅ Normalize Modules (raw → Module table)
# ------------------------------------------------------------
# def normalize_modules(raw: dict) -> list[dict]:
#     """
#     Normalize raw module data from inventory collection into DB-ready dicts.
#     """
#     modules = []
#     for entry_name, v in raw.get("modules", {}).items():
#         modules.append({
#             "name": entry_name.strip(),
#             "description": v.get("descr") or v.get("description"),
#             "part_number": v.get("pid") or v.get("part_number"),
#             "serial_number": v.get("sn") or v.get("serial_number"),
#             "hw_revision": v.get("hw_rev") or v.get("vid") or v.get("hardware_revision"),
#             "under_warranty": v.get("under_warranty", False),   
#             "warranty_expiry": v.get("warranty_expiry"),
#             "environment_status": v.get("environment_status"),
#             "last_updated": datetime.utcnow(),
#         })
#     return modules
def normalize_modules(raw: dict) -> list[dict]:
    """
    Normalize raw module data from inventory collection into DB-ready dicts.
    Handles both list and dict formats, with logging.
    """
    modules = []
    raw_modules = raw.get("modules", [])

    if isinstance(raw_modules, dict):
        iterable = raw_modules.items()
    elif isinstance(raw_modules, list):
        iterable = enumerate(raw_modules)
    else:
        fail_logger.error(
            f"Unexpected modules format for device {raw.get('host_info', {}).get('hostname')}: {type(raw_modules)}"
        )
        return modules

    for entry_name, v in iterable:
        try:
            module = {
                "name": str(entry_name).strip(),
                "description": v.get("descr") or v.get("description"),
                "part_number": v.get("pid") or v.get("part_number"),
                "serial_number": v.get("sn") or v.get("serial_number"),
                "hw_revision": v.get("hw_rev") or v.get("vid") or v.get("hardware_revision"),
                "under_warranty": v.get("under_warranty", False),
                "warranty_expiry": v.get("warranty_expiry"),
                "environment_status": v.get("environment_status"),
                "last_updated": datetime.utcnow(),
            }
            modules.append(module)
        except Exception as e:
            fail_logger.error(
                f"Failed to normalize module entry {entry_name} for device {raw.get('host_info', {}).get('hostname')}: {e}",
                exc_info=True,
            )

    success_logger.info(
        f"Normalized {len(modules)} modules for device {raw.get('host_info', {}).get('hostname')}"
    )
    return modules


def normalize_software_info(raw):
    host = raw.get("host_info", {})

    return {
        "os_version": host.get("version"),
        "firmware_version": host.get("firmware"),  # may be None
    }


def normalize_running_config(raw):
    return raw.get("running_config")

def normalize_routing_table(raw):
    return raw.get("routing_table")

def normalize_mac_table(raw):
    return raw.get("mac_table")

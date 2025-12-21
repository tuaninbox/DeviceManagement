# app/normalizers/device_normalizer.py

from datetime import timedelta
import re


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
def normalize_modules(raw: dict) -> list:
    modules = raw.get("modules", [])

    normalized = []
    for mod in modules:
        normalized.append({
            "description": mod.get("model"),
            "serial_number": mod.get("serial"),
            "part_number": None,
            "warranty_from": None,
            "warranty_expiry": None,
            "environment_status": None,
        })

    return normalized

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

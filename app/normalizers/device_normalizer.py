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
def parse_uptime(uptime):
    if not uptime:
        return None

    # -----------------------------------------
    # Case 1: NX-OS dict format
    # -----------------------------------------
    if isinstance(uptime, dict):
        days = uptime.get("days", 0)
        hours = uptime.get("hours", 0)
        minutes = uptime.get("minutes", 0)
        seconds = uptime.get("seconds", 0)

        return (
            days * 24 * 3600 +
            hours * 3600 +
            minutes * 60 +
            seconds
        )

    # -----------------------------------------
    # Case 2: IOS / IOS-XE string format
    # -----------------------------------------
    if isinstance(uptime, str):
        # Add support for "years"
        pattern = r"(\d+)\s+(year|week|day|hour|minute|second)s?"
        matches = re.findall(pattern, uptime.lower())

        total_seconds = 0
        for value, unit in matches:
            value = int(value)

            if unit == "year":
                total_seconds += value * 365 * 24 * 3600
            elif unit == "week":
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

    # Unknown format
    return None


# Detect Module Types
def classify_module_type(description: str, part_number: str = "", name: str = "") -> str:
    """
    Classify module type across IOS-XE, NX-OS, and other platforms.
    Name (nm) is checked first because it is the strongest indicator.
    """

    desc = (description or "").upper()
    pn = (part_number or "").upper()
    nm = (name or "").upper()

    # --- SFP / Transceiver (highest priority) ---
    sfp_keywords = [
        "SFP", "SFP+", "SFP28", "QSFP", "QSFP+", "QSFP28",
        "GLC", "XFP", "GBIC", "TRANSCEIVER", "GE SX", "GE LX"
    ]
    if any(k in nm for k in sfp_keywords) or \
       any(k in desc for k in sfp_keywords) or \
       any(k in pn for k in sfp_keywords):
        return "SFP"

    # --- Power Supply (must come BEFORE chassis) ---
    psu_keywords = ["POWER SUPPLY", "PWR", "AC", "DC"]
    if any(k in nm for k in psu_keywords) or \
       any(k in desc for k in psu_keywords) or \
       any(k in pn for k in psu_keywords):
        return "POWER_SUPPLY"

    # --- Fan / Cooling (must come BEFORE chassis) ---
    fan_keywords = ["FAN", "COOLING"]
    if any(k in nm for k in fan_keywords) or \
       any(k in desc for k in fan_keywords):
        return "FAN"

    # --- Route Processor / Supervisor ---
    rp_keywords = ["ROUTE PROCESSOR", "RP", "SUPERVISOR", "SUP"]
    if any(k in nm for k in rp_keywords) or \
       any(k in desc for k in rp_keywords) or \
       "R0" in nm or "R1" in nm:
        return "ROUTE_PROCESSOR"

    # --- Line Card / IO Module ---
    io_keywords = ["LINE CARD", "LC", "I/O", "IO", "ETHERNET MODULE"]
    if (any(k in nm for k in io_keywords) or \
        any(k in desc for k in io_keywords)) and \
        "TRANSCEIVER" not in desc:
        return "LINE_CARD"

    # --- Chassis (must come AFTER PSU, FAN, RP, LC) ---
    chassis_keywords = ["CHASSIS", "SYSTEM", "BASE", "ROUTER", "SWITCH"]
    if any(k in nm for k in chassis_keywords) or \
       any(k in desc for k in chassis_keywords):
        return "CHASSIS"

    # --- Default ---
    return "OTHER"


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
def normalize_interfaces(raw: dict) -> list[dict]:
    interfaces = raw.get("interfaces", [])
    if not isinstance(interfaces, list):
        # If it's a dict with error info, bail out gracefully
        return []

    normalized = []
    for iface in interfaces:
        if not isinstance(iface, dict):
            continue
        normalized.append({
            "name": iface.get("name"),
            "type": iface.get("type"),
            "status": iface.get("status"),
            "line_protocol": iface.get("line_protocol"),
            "description": iface.get("description"),
            "mac_address": iface.get("mac_address"),
            "mtu": iface.get("mtu"),
            "speed": iface.get("speed"),
            "duplex": iface.get("duplex"),
            "auto_mdix": iface.get("auto_mdix"),
            "media_type": iface.get("media_type"),
            "auto_negotiate": iface.get("auto_negotiate"),
            "ip_address": iface.get("ip_address"),
            "prefix_length": iface.get("prefix_length"),
            "vrf": iface.get("vrf"),
            "last_updated": datetime.now(),
            "link_down_reason": iface.get("link_down_reason"),
            "port_mode": iface.get("port_mode"),
            "fec_mode": iface.get("fec_mode"),
            "last_link_flapped": iface.get("last_link_flapped"),
        })
    return normalized



# ------------------------------------------------------------
# ✅ Normalize Modules (raw → Module table)
# ------------------------------------------------------------
def normalize_modules(raw: dict) -> list[dict]:
    """
    Normalize raw module data from inventory collection into DB-ready dicts.
    Supports IOS-XE 'show inventory' and NX-OS 'show interface transceiver'.
    """
    modules = []
    raw_modules = raw.get("modules", {})

    # -----------------------------
    # Validate input format
    # -----------------------------
    if isinstance(raw_modules, dict):
        iterable = raw_modules.items()
    elif isinstance(raw_modules, list):
        iterable = enumerate(raw_modules)
    else:
        fail_logger.error(
            f"Unexpected modules format for device {raw.get('host_info', {}).get('hostname')}: {type(raw_modules)}"
        )
        return modules

    # -----------------------------
    # Process each module entry
    # -----------------------------
    for entry_name, v in iterable:
        try:
            # ---------------------------------------------------------
            # 1. NX-OS SFP DETECTION (show interface transceiver)
            # ---------------------------------------------------------
            if v.get("transceiver_present"):
                modules.append({
                    "name": v.get("name") or str(entry_name).strip(),
                    "module_type": "SFP",
                    "description": v.get("transceiver_type"),
                    "part_number": v.get("part_number") or v.get("cis_part_number"),
                    "serial_number": v.get("serial_number"),
                    "hw_revision": v.get("revision"),
                    "vendor": v.get("vendor"),
                    "nominal_bitrate": v.get("nominal_bitrate"),
                    "product_id": v.get("product_id"),
                    "last_updated": datetime.now(),
                    "transceiver_type": v.get("transceiver_type"),
                    "revision": v.get("revision"),
                    "wavelength": v.get("wavelength"),
                    "dom_temperature": v.get("temperature"), 
                    "dom_rx_power": v.get("rx_power"),
                    "dom_tx_power": v.get("tx_power"), 
                    "dom_voltage": v.get("voltage"), 
                    "dom_bias_current": v.get("bias_current"),

                    # interface mapping
                    "interface_name": v.get("interface") or str(entry_name).strip(),
                    "interface_id": None,  # filled in later by sync
                })
                continue

            # ---------------------------------------------------------
            # 2. IOS-XE INVENTORY MODULES (show inventory)
            # ---------------------------------------------------------
            description = v.get("descr") or v.get("description")
            part_number = v.get("pid") or v.get("part_number")
            name = v.get("name") or str(entry_name).strip()

            module_type = classify_module_type(description, part_number, name)

            module = {
                "name": name,
                "description": description,
                "part_number": part_number,
                "serial_number": v.get("sn") or v.get("serial_number"),
                "hw_revision": v.get("hw_revision") or v.get("vid") or v.get("hardware_revision"),
                "under_warranty": v.get("under_warranty", False),
                "warranty_expiry": v.get("warranty_expiry"),
                "environment_status": v.get("environment_status"),
                "last_updated": datetime.now(),
                "module_type": module_type,
            }

            # ---------------------------------------------------------
            # 3. IOS-XE SFP (transceiver modules)
            # ---------------------------------------------------------
            if module_type == "SFP":
                module["interface_name"] = v.get("interface") or v.get("port")
                module["interface_id"] = v.get("interface_id")  # resolved later

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

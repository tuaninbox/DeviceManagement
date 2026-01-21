# core/os_detection.py

from netmiko.ssh_autodetect import SSHDetect

# Map Netmiko autodetect → your internal OS names
OS_MAP = {
    "cisco_ios": "ios",
    "cisco_iosxe": "iosxe",
    "cisco_nxos": "nxos",
    "dell_os10": "dellos10",
    "juniper_junos": "junos",
    "fortinet": "fortios",
    "cisco_wlc": "aironet",
    "f5_tmsh": "f5",
}


def detect_os(ip: str, username: str, password: str, port: int = 22) -> str:
    """
    Uses Netmiko SSHDetect to guess the OS of a device.
    Returns a Netmiko device_type string (e.g., 'cisco_ios').
    Returns 'unknown' if detection fails.
    """
    try:
        guesser = SSHDetect(
            device_type="autodetect",
            host=ip,
            username=username,
            password=password,
            port=port,
        )
        detected = guesser.autodetect()
        return detected or "unknown"
    except Exception:
        return "unknown"


def normalize_os(netmiko_type: str) -> str:
    """
    Converts Netmiko device_type → your internal OS string.
    Returns 'unknown' if not recognized.
    """
    return OS_MAP.get(netmiko_type, "unknown")

from netmiko.ssh_autodetect import SSHDetect
from ..credentials import get_credentials

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

def classify_device_type(model: str, vendor: str) -> str:
    """
    Classify device type based on hardware platform and vendor.
    Returns: switch / router / firewall / load-balancer / unknown
    """

    if not model:
        return "unknown"

    m = model.lower()

    # -------------------------
    # Cisco Switches
    # -------------------------
    if any(x in m for x in [
        "c9300", "c9400", "c9500", "c9600",
        "c9200", "c3850", "c3650", "c2960", "n9k", "n7k", "n5k"
    ]):
        return "switch"

    # -------------------------
    # Cisco Routers
    # -------------------------
    if any(x in m for x in [
        "isr", "asr", "csr", "c8", "c11", "c12", "c89", "c111", "c112"
    ]):
        return "router"

    # -------------------------
    # Cisco Firewalls
    # -------------------------
    if any(x in m for x in ["asa", "ftd", "firepower"]):
        return "firewall"

    # -------------------------
    # Load Balancers (F5, Citrix)
    # -------------------------
    if vendor == "f5" or "big-ip" in m or "citrix" in m or "netscaler" in m:
        return "load-balancer"

    # -------------------------
    # Default
    # -------------------------
    return "unknown"


def detect_vendor(show_ver: dict) -> str:
    """
    Detect vendor from Genie 'show version' parsed output.
    Accepts only the top-level show_ver dict.
    """

    # IOS / IOS-XE structure
    version_info = show_ver.get("version", {})

    # NX-OS structure
    platform_info = show_ver.get("platform", {})

    # Try IOS / IOS-XE first
    os_field = (version_info.get("os") or "").lower()

    # Try NX-OS next
    if not os_field:
        os_field = (platform_info.get("os") or "").lower()

    # Cisco operating systems
    if os_field in ["ios-xe", "ios", "nx-os"]:
        return "cisco"

    # Other vendors
    if os_field == "junos":
        return "juniper"
    if os_field == "fortios":
        return "fortinet"

    return "unknown"

def main():
    ip = ""
    print("=== OS Detection Test ===")
    if not ip: 
        ip = input("Device IP: ").strip()
    username, password = get_credentials()
    port_input = input("Port (default 22): ").strip()
    port = int(port_input) if port_input else 22

    print("\nDetecting OS via SSHDetect...")
    netmiko_type = detect_os(ip, username, password, port)
    print(f"Netmiko detected: {netmiko_type}")

    normalized = normalize_os(netmiko_type)
    print(f"Normalized OS: {normalized}")

    print("\n=== Vendor + Model + Type Test ===")
    print("NOTE: This requires you to paste Genie 'show version' JSON output.")

    try:
        raw_json = input("\nPaste show version JSON dict (or leave blank to skip): ").strip()
        if raw_json:
            import json
            show_ver = json.loads(raw_json)

            vendor = detect_vendor(show_ver)
            print(f"Vendor: {vendor}")

            # Try to extract model if present
            version_info = show_ver.get("version", {})
            platform_info = show_ver.get("platform", {})
            model = (
                version_info.get("chassis")
                or version_info.get("platform")
                or platform_info.get("hardware", {}).get("model")
                or "unknown"
            )
            print(f"Model: {model}")

            device_type = classify_device_type(model, vendor)
            print(f"Device Type: {device_type}")

    except Exception as e:
        print(f"Error parsing show version JSON: {e}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()

import concurrent.futures
from core.device.config import DeviceConfigCollector
from core.device.inventory import DeviceInventoryCollector
from netmiko import ConnectHandler
from device.os_detection import detect_os, normalize_os
from app.databases.devices import SessionLocal
from app.models.devices import Device

def run_parallel(
    reader,
    cmd,
    username,
    password,
    collector_type: str = "inventory",   # "inventory" or "config"
    config_mode: str = "return",         # "return" or "file"
    filterlist=None,
    sanitizeconfig=True,
    removepassword: int = 15,
    **extra_kwargs
):
    rows = list(reader)
    results = []

    if collector_type == "inventory":
        CollectorClass = DeviceInventoryCollector
        run_method = "get_inventory"
    elif collector_type == "config":
        CollectorClass = DeviceConfigCollector
        run_method = "get_config_to_file" if config_mode == "file" else "get_config"
    else:
        raise ValueError(f"Unsupported collector_type: {collector_type}")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for row in rows:
            if row["Host"].startswith("#"):
                continue
            if filterlist and row["Host"].lower() not in filterlist:
                continue

            os_type = row.get("OS", "").strip().lower()

            # Lazy OS detection
            if not os_type:
                detected = detect_os(row["IP"], username, password, row["Port"])
                os_type = normalize_os(detected)
                row["OS"] = os_type

                # Cache OS in DB
                db = SessionLocal()
                device = db.query(Device).filter(Device.hostname == row["Host"]).first()
                if device:
                    device.os = os_type
                    db.commit()
                db.close()


            device_cmds = cmd.get(os_type, []) if isinstance(cmd, dict) else cmd

            retriever = CollectorClass(
                hostname=row["Host"],
                host=row["IP"],
                os=row["OS"],
                user=username,
                password=password,
                cmdlist=device_cmds,
                port=row["Port"],
                sanitizeconfig=sanitizeconfig,
                removepassword=removepassword,
                location=row["Location"],
                group=row["Group"],
                **extra_kwargs
            )

            futures.append(executor.submit(getattr(retriever, run_method)))

        for future in futures:
            results.append(future.result())

    return results

def run_single_command(device, command: str, username: str, password: str) -> str:
    """
    Executes a single command on a device.
    This is used by the API, not by the collectors.
    """

    device_type_map = {
        "ios": "cisco_ios",
        "iosxe": "cisco_iosxe",
        "nxos": "cisco_nxos",
        "dellos10": "dell_os10",
        "junos": "juniper_junos",
        "fortios": "fortinet",
    }

    device_type = device_type_map.get(device.os)
    if not device_type:
        return f"Unsupported OS type: {device.os}"

    conn = ConnectHandler(
        device_type=device_type,
        host=device.host,
        username=username,
        password=password,
        port=device.port or 22,
    )

    output = conn.send_command(command)
    conn.disconnect()
    return output


def run_commands_on_device(device, commands, username, password):
    """
    Executes multiple commands sequentially for the API.
    """
    results = []
    for cmd in commands:
        output = run_single_command(device, cmd, username, password)
        results.append({"command": cmd, "result": output})
    return results

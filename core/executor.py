import concurrent.futures
from core.device.config import DeviceConfigCollector
from core.device.inventory import DeviceInventoryCollector
from netmiko import ConnectHandler
from app.databases.devices import SessionLocal
from app.models.devices import Device

def run_parallel(
    reader,
    cmd,
    username,
    password,
    collector_type: str = "inventory",
    config_mode: str = "return",
    filterlist=None,
    sanitizeconfig=True,
    removepassword: int = 15,
    **extra_kwargs
):
    rows = list(reader)
    results = []

    # ------------------------------------------------------------
    # 1. Preload OS from DB once (avoids DB reads inside threads)
    # ------------------------------------------------------------
    db = SessionLocal()
    db_devices = db.query(Device).all()
    db_os_map = {d.hostname.lower(): (d.os or "").lower() for d in db_devices}
    db.close()

    # ------------------------------------------------------------
    # 2. Determine collector class
    # ------------------------------------------------------------
    if collector_type == "inventory":
        CollectorClass = DeviceInventoryCollector
        run_method = "get_inventory"
    elif collector_type == "config":
        CollectorClass = DeviceConfigCollector
        run_method = "get_config_to_file" if config_mode == "file" else "get_config"
    else:
        raise ValueError(f"Unsupported collector_type: {collector_type}")

    # ------------------------------------------------------------
    # 3. Threaded execution
    # ------------------------------------------------------------
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []

        for row in rows:
            hostname = row["Host"]

            # Skip commented rows
            if hostname.startswith("#"):
                continue

            # Skip if filtered out
            if filterlist and hostname.lower() not in filterlist:
                continue

            # --------------------------------------------------------
            # Inject OS from DB preload (fast, no DB inside threads)
            # --------------------------------------------------------
            os_type = (row.get("OS") or "").strip().lower()
            if not os_type or os_type == "unknown":
                os_type = db_os_map.get(hostname.lower(), "unknown")
                row["OS"] = os_type

            # --------------------------------------------------------
            # Select commands for this OS
            # --------------------------------------------------------
            device_cmds = cmd.get(os_type, []) if isinstance(cmd, dict) else cmd

            # --------------------------------------------------------
            # Create collector session
            # --------------------------------------------------------
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

        # ------------------------------------------------------------
        # 4. Collect results
        # ------------------------------------------------------------
        for future in futures:
            results.append(future.result())

    # ------------------------------------------------------------
    # 5. Batch update OS in DB (after all threads finish)
    # ------------------------------------------------------------
    db = SessionLocal()
    for row, result in zip(rows, results):
        detected_os = result.get("detected_os")
        if not detected_os or detected_os == "unknown":
            continue

        hostname = row["Host"]
        device = db.query(Device).filter(Device.hostname == hostname).first()
        if device and device.os != detected_os:
            device.os = detected_os

    db.commit()
    db.close()

    return results


    return results


def run_single_command(device, command: str, username: str, password: str) -> str:
    """
    Executes a single command on a device.
    This is used by the API, not by the collectors.
    """

    device_type_map = {
        "ios": "cisco_ios",
        "iosxe": "cisco_xe",
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

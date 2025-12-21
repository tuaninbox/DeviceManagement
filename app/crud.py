from sqlalchemy.orm import Session
from . import models, schemas

def get_device(db: Session, device_id: int):
    return db.query(models.Device).filter(models.Device.id == device_id).first()

# db.query(models.Device): create a SQLAlchemy query object targeting Device table = Select * FROM devices
# offset(skip), default skip = 0 -> skip nothing
# limit(limit), default = 100
# all(): execute the SQL query and returns a list of ORM objects which is models.Device instance
def get_devices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Device).offset(skip).limit(limit).all()

def create_device(db: Session, device: schemas.DeviceCreate):
    db_device = models.Device(**device.dict())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def upsert_device(db: Session, device_data: dict):
    # Find existing device by hostname
    db_device = (
        db.query(models.Device)
        .filter(models.Device.hostname == device_data["hostname"])
        .first()
    )

    if db_device:
        # Update existing fields
        for key, value in device_data.items():
            setattr(db_device, key, value)

    else:
        # Create new device
        db_device = models.Device(**device_data)
        db.add(db_device)

    db.commit()
    db.refresh(db_device)
    return db_device


def upsert_interfaces(db: Session, device_id: int, interfaces: list):
    try:
        # Delete old interfaces
        db.query(models.Interface).filter(
            models.Interface.device_id == device_id
        ).delete()

        # Insert new interfaces
        for iface in interfaces:
            db_iface = models.Interface(
                device_id=device_id,
                name=iface["name"],
                status=iface.get("status"),
                description=iface.get("description"),
                vrf=iface.get("vrf"),
            )
            db.add(db_iface)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to upsert interfaces for device {device_id}: {e}")
        raise


def upsert_modules(db: Session, device_id: int, modules: list):
    try:
        # Delete old modules
        db.query(models.Module).filter(
            models.Module.device_id == device_id
        ).delete()

        # Insert new modules
        for mod in modules:
            db_mod = models.Module(
                device_id=device_id,
                description=mod.get("description"),
                part_number=mod.get("part_number"),
                serial_number=mod.get("serial_number"),
                warranty_from=mod.get("warranty_from"),
                warranty_expiry=mod.get("warranty_expiry"),
                environment_status=mod.get("environment_status"),
            )
            db.add(db_mod)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to upsert modules for device {device_id}: {e}")
        raise


def upsert_software_info(db: Session, device_id: int, sw: dict):
    try:
        os_version = sw.get("os_version")
        firmware_version = sw.get("firmware_version")

        if not os_version:
            return None

        # 1. Ensure global version exists
        version = get_or_create_software_version(db, os_version)

        # 2. Upsert device software info
        db_sw = (
            db.query(models.SoftwareInfo)
            .filter(models.SoftwareInfo.device_id == device_id)
            .first()
        )

        if db_sw:
            db_sw.version_id = version.id
            db_sw.firmware_version = firmware_version
        else:
            db_sw = models.SoftwareInfo(
                device_id=device_id,
                version_id=version.id,
                firmware_version=firmware_version
            )
            db.add(db_sw)

        db.commit()
        db.refresh(db_sw)
        return db_sw

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to upsert software info for device {device_id}: {e}")
        raise


def upsert_vlans(db: Session, device_id: int, vlans: list):
    try:
        db.query(models.VLAN).filter(
            models.VLAN.device_id == device_id
        ).delete()

        for vlan in vlans:
            db_vlan = models.VLAN(
                device_id=device_id,
                vlan_id=vlan["vlan_id"],
                name=vlan.get("name"),
                membership=vlan.get("membership"),
            )
            db.add(db_vlan)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to upsert VLANs for device {device_id}: {e}")
        raise


def upsert_running_config(db: Session, device_id: int, hostname: str, config_text: str):
    try:
        from core.utility.utility import save_text_file

        file_path = save_text_file(hostname, "running_config", config_text)

        db_cfg = (
            db.query(models.RunningConfig)
            .filter(models.RunningConfig.device_id == device_id)
            .first()
        )

        if db_cfg:
            db_cfg.file_path = file_path
        else:
            db_cfg = models.RunningConfig(
                device_id=device_id,
                file_path=file_path
            )
            db.add(db_cfg)

        db.commit()
        db.refresh(db_cfg)
        return db_cfg

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to upsert running config for {hostname}: {e}")
        raise


def upsert_mac_table(db: Session, device_id: int, hostname: str, mac_text: str):
    try:
        from core.utility.utility import save_text_file

        file_path = save_text_file(hostname, "mac_table", mac_text)

        db_mac = (
            db.query(models.MacAddressTable)
            .filter(models.MacAddressTable.device_id == device_id)
            .first()
        )

        if db_mac:
            db_mac.file_path = file_path
        else:
            db_mac = models.MacAddressTable(
                device_id=device_id,
                file_path=file_path
            )
            db.add(db_mac)

        db.commit()
        db.refresh(db_mac)
        return db_mac

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to upsert MAC table for {hostname}: {e}")
        raise

def get_or_create_software_version(db: Session, os_version: str):
    version = (
        db.query(models.SoftwareVersion)
        .filter(models.SoftwareVersion.os_version == os_version)
        .first()
    )

    if version:
        return version

    version = models.SoftwareVersion(
        os_version=os_version,
        type=None,
        category=None,
        vulnerability=None
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version

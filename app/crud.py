from sqlalchemy.orm import Session
from . import models, schemas
from core.logging_manager import setup_loggers
from core.utility.utility import safe_datetime
from app.normalizers.device_normalizer import (
    normalize_serial,
)

# Initialize loggers for this CRUD module
success_logger, fail_logger = setup_loggers(logger_name="app_crud")

def get_device(db: Session, device_id: int):
    return db.query(models.Device).filter(models.Device.id == device_id).first()

# db.query(models.Device): create a SQLAlchemy query object targeting Device table = Select * FROM devices
# offset(skip), default skip = 0 -> skip nothing
# limit(limit), default = 100
# all(): execute the SQL query and returns a list of ORM objects which is models.Device instance
def get_devices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Device).offset(skip).limit(limit).all()

def get_all_devices(db: Session): 
    return db.query(models.Device).all()

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
        db.query(models.Interface).filter(
            models.Interface.device_id == device_id
        ).delete()

        for iface in interfaces:
            db_iface = models.Interface(
                device_id=device_id,
                name=iface.get("name"),
                type=iface.get("type"),
                status=iface.get("status"),
                line_protocol=iface.get("line_protocol"),
                description=iface.get("description"),
                mac_address=iface.get("mac_address"),
                mtu=iface.get("mtu"),
                speed=iface.get("speed"),
                duplex=iface.get("duplex"),
                auto_mdix=iface.get("auto_mdix"),
                media_type=iface.get("media_type"),
                auto_negotiate=iface.get("auto_negotiate"),
                ip_address=iface.get("ip_address"),
                prefix_length=iface.get("prefix_length"),
                vrf=iface.get("vrf"),
                last_updated=safe_datetime(iface.get("last_updated")),
                link_down_reason=iface.get("link_down_reason"),
                port_mode=iface.get("port_mode"),
                fec_mode=iface.get("fec_mode"),
                last_link_flapped=safe_datetime(iface.get("last_link_flapped")),
            )
            db.add(db_iface)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to upsert interfaces for device {device_id}: {e}")
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


def create_module(db: Session, module: schemas.ModuleCreate):
    db_module = models.Module(
        device_id=module.device_id,
        module_type=module.module_type,
        name=module.name,
        description=module.description,
        part_number=module.part_number,
        serial_number=module.serial_number,
        hw_revision=module.hw_revision,
        under_warranty=module.under_warranty,
        warranty_expiry=module.warranty_expiry,
        environment_status=module.environment_status,
        last_updated=module.last_updated,
    )
    db.add(db_module)
    db.commit()
    db.refresh(db_module)
    return db_module


def create_sfp_module(db: Session, sfp: schemas.SfpModuleCreate):
    db_sfp = models.SfpModule(
        module_id=sfp.module_id,
        interface=sfp.interface,
        interface_id=sfp.interface_id,
        transceiver_type=sfp.transceiver_type,
        vendor=sfp.vendor,
        nominal_bitrate=sfp.nominal_bitrate,
        wavelength=sfp.wavelength,
        product_id=sfp.product_id,
        part_number=sfp.part_number,
        revision=sfp.revision,
        dom_temperature=sfp.dom_temperature,
        dom_rx_power=sfp.dom_rx_power,
        dom_tx_power=sfp.dom_tx_power,
        dom_voltage=sfp.dom_voltage,
        dom_bias_current=sfp.dom_bias_current,
    )
    db.add(db_sfp)
    db.commit()
    db.refresh(db_sfp)
    return db_sfp


def get_modules(db: Session):
    return db.query(models.Module).all()


def upsert_modules(db: Session, device_id: int, modules: list[dict]):
    try:
        # ---------------------------------------------------------
        # 1. Normalize incoming serials and collect valid ones
        # ---------------------------------------------------------
        incoming_serials = {
            normalize_serial(m.get("serial_number"))
            for m in modules
        }
        incoming_serials.discard(None)  # remove invalid serials

        # ---------------------------------------------------------
        # 2. Delete only modules with VALID serials that disappeared
        # ---------------------------------------------------------
        db.query(models.Module).filter(
            models.Module.device_id == device_id,
            models.Module.serial_number.isnot(None),
            models.Module.serial_number != "",
            ~models.Module.serial_number.in_(incoming_serials)
        ).delete(synchronize_session=False)

        db.flush()

        # ---------------------------------------------------------
        # 3. Upsert each module
        # ---------------------------------------------------------
        for mod in modules:
            serial = normalize_serial(mod.get("serial_number"))

            # Try to find existing module by serial (only if valid)
            existing = None
            if serial:
                existing = db.query(models.Module).filter(
                    models.Module.device_id == device_id,
                    models.Module.serial_number == serial
                ).first()

            if existing:
                # -------------------------
                # UPDATE EXISTING MODULE
                # -------------------------
                existing.module_type = mod.get("module_type", existing.module_type)
                existing.name = mod.get("name", existing.name)
                existing.description = mod.get("description", existing.description)
                existing.part_number = mod.get("part_number", existing.part_number)
                existing.hw_revision = mod.get("hw_revision", existing.hw_revision)
                existing.environment_status = mod.get("environment_status", existing.environment_status)

                # Only update warranty fields if incoming data is NOT None
                if mod.get("under_warranty") is not None:
                    existing.under_warranty = mod["under_warranty"]

                if mod.get("warranty_expiry") is not None:
                    existing.warranty_expiry = mod["warranty_expiry"]

                # Update last_updated only if provided
                new_last = safe_datetime(mod.get("last_updated"))
                if new_last:
                    existing.last_updated = new_last

                db_mod = existing

            else:
                # -------------------------
                # INSERT NEW MODULE
                # -------------------------
                db_mod = models.Module(
                    device_id=device_id,
                    module_type=mod.get("module_type", "OTHER"),
                    name=mod.get("name"),
                    description=mod.get("description"),
                    part_number=mod.get("part_number"),
                    serial_number=serial,  # may be None
                    hw_revision=mod.get("hw_revision"),
                    under_warranty=mod.get("under_warranty", False),
                    warranty_expiry=mod.get("warranty_expiry"),
                    environment_status=mod.get("environment_status"),
                    last_updated=safe_datetime(mod.get("last_updated")),
                )
                db.add(db_mod)
                db.flush()

            # ---------------------------------------------------------
            # 4. Handle SFP submodules (UPSERT)
            # ---------------------------------------------------------
            if mod.get("module_type") == "SFP":

                raw_ifname = mod.get("interface_name")

                # Try exact match
                iface = db.query(models.Interface).filter(
                    models.Interface.device_id == device_id,
                    models.Interface.name == raw_ifname
                ).first()

                # Try suffix match
                if not iface and isinstance(raw_ifname, str) and raw_ifname.strip():
                    iface = (
                        db.query(models.Interface)
                        .filter(models.Interface.device_id == device_id)
                        .filter(models.Interface.name.endswith(raw_ifname))
                        .first()
                    )
                    if iface:
                        mod["interface_name"] = iface.name

                interface_id = iface.id if iface else None

                # Try to find existing SFP
                existing_sfp = db.query(models.SfpModule).filter(
                    models.SfpModule.module_id == db_mod.id,
                    models.SfpModule.interface_name == mod.get("interface_name")
                ).first()

                if existing_sfp:
                    # UPDATE SFP
                    for field in [
                        "transceiver_type", "vendor", "nominal_bitrate",
                        "wavelength", "product_id", "part_number", "revision",
                        "dom_temperature", "dom_rx_power", "dom_tx_power",
                        "dom_voltage", "dom_bias_current"
                    ]:
                        value = mod.get(field)
                        if value is not None:
                            setattr(existing_sfp, field, value)

                else:
                    # INSERT NEW SFP
                    db_sfp = models.SfpModule(
                        module_id=db_mod.id,
                        interface_name=mod.get("interface_name"),
                        interface_id=interface_id,
                        transceiver_type=mod.get("transceiver_type"),
                        vendor=mod.get("vendor"),
                        nominal_bitrate=mod.get("nominal_bitrate"),
                        wavelength=mod.get("wavelength"),
                        product_id=mod.get("product_id"),
                        part_number=mod.get("part_number"),
                        revision=mod.get("revision"),
                        dom_temperature=mod.get("dom_temperature"),
                        dom_rx_power=mod.get("dom_rx_power"),
                        dom_tx_power=mod.get("dom_tx_power"),
                        dom_voltage=mod.get("dom_voltage"),
                        dom_bias_current=mod.get("dom_bias_current"),
                    )
                    db.add(db_sfp)

        # ---------------------------------------------------------
        # 5. Commit all changes
        # ---------------------------------------------------------
        db.commit()
        success_logger.info(f"Upserted {len(modules)} modules for device {device_id}")

    except Exception as e:
        db.rollback()
        fail_logger.error(
            f"Failed to upsert modules for device {device_id}: {e}",
            exc_info=True
        )
        raise


# def upsert_modules(db: Session, device_id: int, modules: list[dict]):
#     try:
#         # Delete old modules (cascade deletes SFP submodules)
#         db.query(models.Module).filter(
#             models.Module.device_id == device_id
#         ).delete()
#         db.commit()

#         for mod in modules:
#             # 1. Insert base module
#             db_mod = models.Module(
#                 device_id=device_id,
#                 module_type=mod.get("module_type", "OTHER"),
#                 name=mod.get("name"),
#                 description=mod.get("description"),
#                 part_number=mod.get("part_number"),
#                 serial_number=mod.get("serial_number"),
#                 hw_revision=mod.get("hw_revision"),
#                 under_warranty=mod.get("under_warranty", False),
#                 warranty_expiry=mod.get("warranty_expiry"),
#                 environment_status=mod.get("environment_status"),
#                 last_updated=safe_datetime(mod.get("last_updated")),
#             )
#             db.add(db_mod)
#             db.flush()  # get db_mod.id without commit

#             # 2. Insert SFP subtype if applicable
#             if mod.get("module_type") == "SFP":

#                 raw_ifname = mod.get("interface_name")

#                 # 1. Try exact match first (NX-OS, IOS-XE switches)
#                 iface = db.query(models.Interface).filter(
#                     models.Interface.device_id == device_id,
#                     models.Interface.name == raw_ifname
#                 ).first()

#                 # 2. If not found, try suffix match (IOS-XE routers)
#                 if not iface:
#                     # Only attempt suffix match if raw_ifname is a real string
#                     if isinstance(raw_ifname, str) and raw_ifname.strip():
#                         iface = (
#                             db.query(models.Interface)
#                             .filter(models.Interface.device_id == device_id)
#                             .filter(models.Interface.name.endswith(raw_ifname))
#                             .first()
#                         )

#                     # If suffix match found, update interface_name to full name
#                     if iface:
#                         mod["interface_name"] = iface.name

#                 interface_id = iface.id if iface else None

#                 db_sfp = models.SfpModule(
#                     module_id=db_mod.id,
#                     interface_name=mod.get("interface_name"),
#                     interface_id=interface_id,
#                     transceiver_type=mod.get("transceiver_type"),
#                     vendor=mod.get("vendor"),
#                     nominal_bitrate=mod.get("nominal_bitrate"),
#                     wavelength=mod.get("wavelength"),
#                     product_id=mod.get("product_id"),
#                     part_number=mod.get("part_number"),
#                     revision=mod.get("revision"),
#                     dom_temperature=mod.get("dom_temperature"),
#                     dom_rx_power=mod.get("dom_rx_power"),
#                     dom_tx_power=mod.get("dom_tx_power"),
#                     dom_voltage=mod.get("dom_voltage"),
#                     dom_bias_current=mod.get("dom_bias_current"),
#                 )
#                 db.add(db_sfp)


#         db.commit()
#         success_logger.info(f"Upserted {len(modules)} modules for device {device_id}")

#     except Exception as e:
#         db.rollback()
#         fail_logger.error(
#             f"Failed to upsert modules for device {device_id}: {e}",
#             exc_info=True
#         )
#         raise


# SQLAlchemy ORM Models
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone
from ..databases.devices import Base

# Base = declarative_base()

# -------------------------
# Devices
# -------------------------
class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, nullable=False)
    mgmt_address = Column(String, nullable=False)
    port = Column(Integer, nullable=False, default=22)

    vrf = Column(String)
    location = Column(String)
    device_group = Column(String)
    uptime = Column(Integer)
    model = Column(String)
    vendor = Column(String, nullable=True)
    os = Column(String, nullable=True)
    type = Column(String, nullable=True)
    serial_number = Column(String)
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Git-backed file paths
    running_config_path = Column(String)
    routing_table_path = Column(String)
    mac_table_path = Column(String)

    # Relationships
    software_info = relationship("SoftwareInfo", back_populates="device", uselist=False)
    modules = relationship("Module", back_populates="device", cascade="all, delete-orphan")
    interfaces = relationship("Interface", back_populates="device", cascade="all, delete-orphan")
    vlans = relationship("VLAN", back_populates="device", cascade="all, delete-orphan")


# -------------------------
# Software Version
# -------------------------
class SoftwareVersion(Base):
    __tablename__ = "software_versions"

    id = Column(Integer, primary_key=True, index=True)
    os_version = Column(String, unique=True, nullable=False)

    type = Column(String)        # e.g., "IOS-XE", "NX-OS", "IOS-XR"
    category = Column(String)    # e.g., "Network OS", "Switch OS", "Router OS"

    vulnerability = Column(Text)  # JSON or text describing CVEs
    last_scanned = Column( DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) )

    devices = relationship("SoftwareInfo", back_populates="version")


# -------------------------
# Software Information
# -------------------------
class SoftwareInfo(Base):
    __tablename__ = "software_info"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    version_id = Column(Integer, ForeignKey("software_versions.id"))
    firmware_version = Column(String)
    last_updated = Column( DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) )
    device = relationship("Device", back_populates="software_info")
    version = relationship("SoftwareVersion", back_populates="devices")


# -------------------------
# Interfaces
# -------------------------
class Interface(Base):
    __tablename__ = "interfaces"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))

    name = Column(String)
    type = Column(String)
    status = Column(String)
    line_protocol = Column(String)
    description = Column(String)
    mac_address = Column(String)
    mtu = Column(Integer)
    speed = Column(String)
    duplex = Column(String)
    auto_mdix = Column(String)
    media_type = Column(String)
    auto_negotiate = Column(String)
    ip_address = Column(String)
    prefix_length = Column(Integer)
    vrf = Column(String)
    last_updated = Column( DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    link_down_reason = Column(String)
    port_mode = Column(String)
    fec_mode = Column(String)
    last_link_flapped = Column( DateTime(timezone=True))

    # Relationships
    device = relationship("Device", back_populates="interfaces")

    # One SFP per interface (optional)
    sfp_module = relationship("SfpModule", back_populates="interface_rel", uselist=False)

# -------------------------
# Modules
# -------------------------
class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))

    module_type = Column(String)
    name = Column(String)
    description = Column(String)
    part_number = Column(String)
    serial_number = Column(String)
    hw_revision = Column(String)
    under_warranty = Column(Boolean, default=False)
    warranty_expiry = Column(Date)
    environment_status = Column(String)
    last_updated = Column( DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    device = relationship("Device", back_populates="modules")

    # Optional SFP subtype
    sfp_module = relationship("SfpModule", back_populates="module", uselist=False, cascade="all, delete-orphan")


class SfpModule(Base):
    __tablename__ = "sfp_modules"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"))
    interface_id = Column(Integer, ForeignKey("interfaces.id", ondelete="SET NULL"))

    interface_name = Column(String)
    transceiver_type = Column(String)
    vendor = Column(String)
    nominal_bitrate = Column(String)
    wavelength = Column(String)
    product_id = Column(String)
    part_number = Column(String)
    revision = Column(String)
    dom_temperature = Column(String)
    dom_rx_power = Column(String)
    dom_tx_power = Column(String)
    dom_voltage = Column(String)
    dom_bias_current = Column(String)

    # Relationships
    module = relationship("Module", back_populates="sfp_module")
    interface_rel = relationship("Interface", back_populates="sfp_module")

# -------------------------
# VLANs
# -------------------------
class VLAN(Base):
    __tablename__ = "vlans"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    vlan_id = Column(Integer, nullable=False)
    name = Column(String)
    membership = Column(Text)
    last_updated = Column( DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) )

    device = relationship("Device", back_populates="vlans")

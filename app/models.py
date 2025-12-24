# SQLAlchemy ORM Models
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from .database import Base

Base = declarative_base()

# -------------------------
# Devices
# -------------------------
class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, nullable=False)
    mgmt_address = Column(String, nullable=False)
    vrf = Column(String)
    location = Column(String)
    device_group = Column(String)
    uptime = Column(Integer)
    model = Column(String)
    serial_number = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    software_info = relationship("SoftwareInfo", back_populates="device", uselist=False)
    modules = relationship("Module", back_populates="device")
    interfaces = relationship("Interface", back_populates="device")
    running_configs = relationship("RunningConfig", back_populates="device")
    routing_table = relationship("RoutingTable", back_populates="device")
    mac_address_table = relationship("MacAddressTable", back_populates="device")
    vlans = relationship("VLAN", back_populates="device")

# class DeviceModel(Base):
#     __tablename__ = "devices"

#     id = Column(Integer, primary_key=True, index=True)
#     hostname = Column(String, index=True)
#     mgmt_address = Column(String)
#     model = Column(String)
#     serial_number = Column(String)

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
    last_scanned = Column(DateTime, default=datetime.utcnow)

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
    last_updated = Column(DateTime, default=datetime.utcnow)
    device = relationship("Device", back_populates="software_info")
    version = relationship("SoftwareVersion", back_populates="devices")



# -------------------------
# Modules
# -------------------------
class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    description = Column(Text)
    part_number = Column(String)
    serial_number = Column(String)
    hw_revision = Column(String)
    under_warranty = Column(Boolean, default=False)
    warranty_expiry = Column(Date)
    environment_status = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="modules")
    interfaces = relationship("Interface", back_populates="sfp_module")



# -------------------------
# Interfaces
# -------------------------
class Interface(Base):
    __tablename__ = "interfaces"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    status = Column(String)
    description = Column(Text)
    vrf = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    sfp_module_id = Column(Integer, ForeignKey("modules.id", ondelete="SET NULL"))

    device = relationship("Device", back_populates="interfaces")
    sfp_module = relationship("Module", back_populates="interfaces")


# -------------------------
# Running Configuration
# -------------------------
class RunningConfig(Base):
    __tablename__ = "running_config"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))

    # ✅ Store file path instead of full config text
    file_path = Column(String, nullable=False)

    updated_by = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="running_configs")



# -------------------------
# Routing Table
# -------------------------
class RoutingTable(Base):
    __tablename__ = "routing_table"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    vrf = Column(String, default="default")
    route = Column(String, nullable=False)
    next_hop = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="routing_table")


# -------------------------
# MAC Address Table
# -------------------------
class MacAddressTable(Base):
    __tablename__ = "mac_address_table"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    vrf = Column(String, default="default")
    mac_address = Column(String, nullable=False)
    interface_name = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="mac_address_table")


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
    last_updated = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="vlans")

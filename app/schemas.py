# Pydantic Models for FastAPI
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

# -------------------------
# Base Schemas
# -------------------------
class SoftwareVersionBase(BaseModel):
    id: int
    os_version: str
    type: Optional[str]
    category: Optional[str]
    vulnerability: Optional[str]
    last_scanned: datetime

    class Config:
        from_attributes = True

class SoftwareInfoBase(BaseModel):
    firmware_version: Optional[str]
    last_updated: Optional[datetime]

class ModuleBase(BaseModel):
    name: Optional[str]
    description: Optional[str]
    part_number: Optional[str]
    serial_number: Optional[str]
    hw_revision: Optional[str]
    under_warranty: Optional[bool] = False
    warranty_expiry: Optional[date]
    environment_status: Optional[str]
    last_updated: Optional[datetime]

class InterfaceBase(BaseModel):
    name: str
    type: Optional[str] = None
    status: Optional[str] = None
    line_protocol: Optional[str] = None
    description: Optional[str] = None
    mac_address: Optional[str] = None
    mtu: Optional[int] = None
    speed: Optional[str] = None
    duplex: Optional[str] = None
    auto_mdix: Optional[str] = None
    media_type: Optional[str] = None
    auto_negotiate: Optional[bool] = None
    ip_address: Optional[str] = None
    prefix_length: Optional[str] = None
    vrf: Optional[str] = None
    link_down_reason: Optional[str] = None
    port_mode: Optional[str] = None
    fec_mode: Optional[str] = None
    last_link_flapped: Optional[str] = None

    last_updated: Optional[datetime] = None
    sfp_module_id: Optional[int] = None


class RunningConfigBase(BaseModel):
    config: Optional[str]
    updated_by: Optional[str]
    last_updated: Optional[datetime]

class RoutingTableBase(BaseModel):
    vrf: Optional[str] = "default"
    route: str
    next_hop: Optional[str]
    last_updated: Optional[datetime]

class MacAddressTableBase(BaseModel):
    vrf: Optional[str] = "default"
    mac_address: str
    interface_name: Optional[str]
    last_updated: Optional[datetime]

class VLANBase(BaseModel):
    vlan_id: int
    name: Optional[str]
    membership: Optional[str]
    last_updated: Optional[datetime]

# -------------------------
# Device Schemas
# -------------------------
class DeviceBase(BaseModel):
    hostname: str
    mgmt_address: str
    vrf: Optional[str]
    location: Optional[str]
    device_group: Optional[str]
    uptime: Optional[int]
    model: Optional[str]
    serial_number: Optional[str]
    last_updated: Optional[datetime]

# -------------------------
# Create Schemas (for POST)
# -------------------------
class DeviceCreate(DeviceBase):
    pass

class SoftwareInfoCreate(SoftwareInfoBase):
    pass

class ModuleCreate(ModuleBase):
    pass

class InterfaceCreate(InterfaceBase):
    pass

class RunningConfigCreate(RunningConfigBase):
    pass

class RoutingTableCreate(RoutingTableBase):
    pass

class MacAddressTableCreate(MacAddressTableBase):
    pass

class VLANCreate(VLANBase):
    pass

# -------------------------
# Response Schemas (with IDs + relationships)
# -------------------------
class SoftwareInfo(SoftwareInfoBase):
    id: int
    version: SoftwareVersionBase
    class Config:
        from_attributes = True

class Module(ModuleBase):
    id: int
    class Config:
        from_attributes = True

class Interface(InterfaceBase):
    id: int
    class Config:
        from_attributes = True

class RunningConfig(RunningConfigBase):
    id: int
    class Config:
        from_attributes = True

class RoutingTable(RoutingTableBase):
    id: int
    class Config:
        from_attributes = True

class MacAddressTable(MacAddressTableBase):
    id: int
    class Config:
        from_attributes = True

class VLAN(VLANBase):
    id: int
    class Config:
        from_attributes = True

class Device(DeviceBase):
    id: int
    software_info: Optional[SoftwareInfo]
    modules: List[Module] = []
    interfaces: List[Interface] = []
    running_configs: List[RunningConfig] = []
    routing_table: List[RoutingTable] = []
    mac_address_table: List[MacAddressTable] = []
    vlans: List[VLAN] = []

    class Config:
        from_attributes = True

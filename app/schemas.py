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
    module_type: Optional[str]  # "SFP", "PSU", "FAN", etc.
    name: Optional[str]
    description: Optional[str]
    part_number: Optional[str]
    serial_number: Optional[str]
    hw_revision: Optional[str]

    under_warranty: Optional[bool] = False
    warranty_expiry: Optional[date]
    environment_status: Optional[str]
    last_updated: Optional[datetime]

    class Config:
        from_attributes = True


class SfpModuleBase(BaseModel):
    interface_name: Optional[str]          # normalized interface name
    interface_id: Optional[int]       # FK to interface table

    transceiver_type: Optional[str]
    vendor: Optional[str]
    nominal_bitrate: Optional[int]
    wavelength: Optional[int]

    product_id: Optional[str]
    part_number: Optional[str]
    revision: Optional[str]

    dom_temperature: Optional[float]
    dom_rx_power: Optional[float]
    dom_tx_power: Optional[float]
    dom_voltage: Optional[float]
    dom_bias_current: Optional[float]

    class Config:
        from_attributes = True


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
    prefix_length: Optional[int] = None
    vrf: Optional[str] = None
    link_down_reason: Optional[str] = None
    port_mode: Optional[str] = None
    fec_mode: Optional[str] = None
    last_link_flapped: Optional[str] = None
    last_updated: Optional[datetime] = None

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

    # Git‑tracked file paths
    running_config_path: Optional[str]
    routing_table_path: Optional[str]
    mac_table_path: Optional[str]


# -------------------------
# Create Schemas (for POST)
# -------------------------

class DeviceCreate(DeviceBase):
    pass


class SoftwareInfoCreate(SoftwareInfoBase):
    pass


class ModuleCreate(ModuleBase):
    device_id: int
    module_type: str
    name: str


class SfpModuleCreate(SfpModuleBase):
    module_id: int


class InterfaceCreate(InterfaceBase):
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


class SfpModule(SfpModuleBase):
    id: int
    module_id: int

    class Config:
        from_attributes = True


class Module(ModuleBase):
    id: int
    sfp_module: Optional[SfpModule] = None   # UPDATED: correct field name

    class Config:
        from_attributes = True


class Interface(InterfaceBase):
    id: int
    sfp_module: Optional[SfpModule] = None   # Optional: expose SFP on interface

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
    vlans: List[VLAN] = []

    class Config:
        from_attributes = True

class SyncRequest(BaseModel):
    hostnames: Optional[List[str]] = None

class SyncEoxRequest(BaseModel):
    serial_numbers: Optional[List[str]] = None
    device_ids: Optional[List[int]] = None


class DeviceListResponse(BaseModel):
    items: List[Device]
    total: int
    page: int
    page_size: int

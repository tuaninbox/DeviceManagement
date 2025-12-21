# Device Table
```
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT NOT NULL UNIQUE,
    mgmt_address TEXT NOT NULL,
    vrf TEXT,
    location TEXT,
    device_group TEXT,
    uptime INTEGER,
    model TEXT,
    serial_number TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

# Software Table
```
CREATE TABLE software_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    os_version TEXT,
    firmware_version TEXT,
    vulnerability TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

```

# Module Table
```
CREATE TABLE modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    description TEXT,
    part_number TEXT,
    serial_number TEXT,
    warranty_from DATE,
    warranty_expiry DATE,
    environment_status TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```

# Interface Table
```
CREATE TABLE interfaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT,
    description TEXT,
    vrf TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sfp_module_id INTEGER,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (sfp_module_id) REFERENCES modules(id) ON DELETE SET NULL
);
```

# Running Configuration Table
```
CREATE TABLE running_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    config TEXT,
    updated_by TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```

# Operational Data Table
## Routing Table
```
CREATE TABLE routing_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    vrf TEXT DEFAULT 'default',
    route TEXT NOT NULL,
    next_hop TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```

# MAC Address Table
```
CREATE TABLE mac_address_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    vrf TEXT DEFAULT 'default',
    mac_address TEXT NOT NULL,
    interface_name TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```

# VLAN Table
```
CREATE TABLE vlans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    vlan_id INTEGER NOT NULL,
    name TEXT,
    membership TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```


from config.config_loader import get_inventory_config
from .static_inventory import StaticInventoryProvider
from .dynamic_inventory import DynamicInventoryProvider

def get_inventory_provider():
    cfg = get_inventory_config()

    inv_type = cfg.get("type", "static")
    source = cfg.get("source")

    if inv_type == "static":
        if not source:
            raise ValueError("Static inventory requires 'source' (CSV file path)")
        return StaticInventoryProvider(source)

    if inv_type == "dynamic":
        # You can later support multiple dynamic sources:
        # e.g., database, netbox, cmdb, cloud, etc.
        return DynamicInventoryProvider(source)

    raise ValueError(f"Unknown inventory type: {inv_type}")

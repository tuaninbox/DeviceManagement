from .inventory_provider import InventoryProvider

# Import Nagios dynamic inventory logic
from core.nagios import get_device_list_from_nagios


class DynamicInventoryProvider(InventoryProvider):
    def __init__(self, source=None):
        self.source = source

    def load(self):
        """
        Load inventory dynamically based on the configured source.
        Currently supports: nagios
        """
        if not self.source:
            raise ValueError("Dynamic inventory requires a 'source' field")

        # ------------------------------------------------------------
        # 1. Nagios dynamic inventory
        # ------------------------------------------------------------
        if self.source.lower() == "nagios":
            return get_device_list_from_nagios()

        # ------------------------------------------------------------
        # 2. Future dynamic sources can be added here
        # ------------------------------------------------------------
        raise ValueError(f"Unsupported dynamic inventory source: {self.source}")

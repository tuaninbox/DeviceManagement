import csv
from .inventory_provider import InventoryProvider

class StaticInventoryProvider(InventoryProvider):
    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        with open(self.file_path) as f:
            return list(csv.DictReader(f))

# from app.databases.inventory import SessionLocal, Device
from .inventory_provider import InventoryProvider

class DynamicInventoryProvider(InventoryProvider):
    # def load(self):
    #     db = SessionLocal()
    #     devices = db.query(Device).all()
    #     return [d.to_dict() for d in devices]
    pass
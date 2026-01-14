from .models import devices
import strawberry
from typing import List, Optional
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.orm import Session
from .databases import devices

def get_db():
    db = devices.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@strawberry.type
class Module:
    id: int
    description: Optional[str]
    part_number: Optional[str]
    serial_number: Optional[str]

@strawberry.type
class Device:
    id: int
    hostname: str
    mgmt_address: str
    model: Optional[str]
    serial_number: Optional[str]
    modules: Optional[List[Module]] = strawberry.field(default_factory=list)

@strawberry.type
class Query:
    @strawberry.field
    def devices(self) -> List[Device]:
        db = next(get_db())
        return db.query(devices.Device).all()
# Mutation root
@strawberry.type
class Mutation:
    @strawberry.mutation
    def addDevice(self, info, hostname: str, mgmtAddress: str, model: str, serialNumber: str) -> Device:
        db: Session = info.context["db"]
        row = devices.Device(hostname=hostname, mgmt_address=mgmtAddress, model=model, serial_number=serialNumber)
        db.add(row)
        db.commit()
        db.refresh(row)
        return Device(id=row.id, hostname=row.hostname, mgmt_address=row.mgmt_address,
                      model=row.model, serial_number=row.serial_number, modules=[])

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)

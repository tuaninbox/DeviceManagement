from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, Any
from datetime import datetime, timezone
import json

# This is timezone that convert to UTC, used with DB that support timezone such as POSTGRESQL
# class UTCModel(BaseModel):
#     model_config = ConfigDict(
#         from_attributes=True,
#         json_encoders={
#             datetime: lambda v: (
#                 v.astimezone(timezone.utc)
#                 .isoformat()
#                 .replace("+00:00", "Z")
#                 if v is not None else None
#             )
#         }
#     )

# This is Model that just add correct format of TZ without converting, used with SQLite which doesn't support timezone
class UTCModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: (
                # Treat naive datetime as UTC, but DO NOT convert
                v.replace(tzinfo=timezone.utc)
                 .isoformat()
                 .replace("+00:00", "Z")
                if v is not None else None
            )
        }
    )


class JobSchema(UTCModel):
    id: str
    category: Optional[str]
    description: Optional[str]
    status: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    result: Optional[Any]
    error: Optional[str]

    class Config:
        orm_mode = True

    @field_validator("result", mode="before")
    def decode_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v
        

class JobCreateSchema(UTCModel):
    category: str
    description: str

class JobUpdateSchema(UTCModel):
    status: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    result: Optional[str]
    error: Optional[str]

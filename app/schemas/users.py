from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

from app.schemas.common import MessageResponse


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


class UserProfileSchema(UTCModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    timezone: str
    language: str
    theme: str
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True

class LocalUserSchema(UTCModel):
    username: str
    roles: List[str]
    is_active: bool

    class Config:
        orm_mode = True

# For both Local and External Users
class UserListItemSchema(UTCModel):
    username: str
    provider: str
    roles: List[str]
    is_active: bool
    full_name: Optional[str]
    email: Optional[str]
    timezone: str
    language: str
    theme: str
    last_login: Optional[datetime]

    class Config:
        orm_mode = True



class AuthStatusResponse(UTCModel):
    authenticated: bool
    user: dict

class ProfileResponse(UTCModel):
    username: str
    full_name: Optional[str]
    email: Optional[str]
    timezone: str
    language: str
    theme: str
    last_login: Optional[datetime]

class MeResponse(UTCModel):
    username: str
    roles: list[str]
    provider: str


from pydantic import BaseModel
from app.schemas.common import MessageResponse


class LoginRequest(BaseModel):
    username: str
    password: str

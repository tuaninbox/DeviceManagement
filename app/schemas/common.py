from pydantic import BaseModel
from typing import Optional, List

class MessageResponse(BaseModel):
    message: str
    username: Optional[str] = None
    roles: Optional[List[str]] = None

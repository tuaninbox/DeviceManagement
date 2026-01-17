import time
from typing import Optional
from jose import jwt, JWTError
from fastapi import Request

from config.auth_loader import get_jwt_config

jwt_config = get_jwt_config()
SECRET_KEY = jwt_config.get("secret_key")
ALGORITHM = jwt_config.get("algorithm")
SESSION_EXPIRE_SECONDS = jwt_config.get("session_expire_seconds")


def create_session_cookie(username: str, roles: list[str] = None):
    if roles is None:
        roles = []

    payload = {
        "sub": username,
        "roles": roles,
        "iat": int(time.time()),
        "exp": int(time.time()) + SESSION_EXPIRE_SECONDS,
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer"
    }



def verify_session_cookie(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

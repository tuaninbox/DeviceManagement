from fastapi import Request, HTTPException, Depends
from app.services.jwt_manager import verify_session_cookie
from config.permissions_loader import PERMISSIONS, expand_roles


def require_auth(request: Request):
    """
    Ensures the user is authenticated and returns the decoded JWT payload.
    """
    user = verify_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_current_user(request: Request):
    """
    Returns a normalized user object:
    {
        "username": "...",
        "roles": ["admin", "operator"]
    }
    """
    user = verify_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # JWT payload should contain username + roles
    return {
        "username": user.get("sub"),
        "roles": user.get("roles", [])
    }


def require_permission(permission: str):
    def wrapper(user = Depends(get_current_user)):
        user_roles = expand_roles(user["roles"])

        for role in user_roles:
            allowed = PERMISSIONS.get(role, [])
            if permission in allowed:
                return user

        raise HTTPException(status_code=403, detail="Forbidden")

    return wrapper



def require_admin(user = Depends(get_current_user)):
    """
    Backwards-compatible admin check.
    Uses the new permission system.
    """
    if "admin" not in user["roles"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user

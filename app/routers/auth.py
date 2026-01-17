from fastapi import APIRouter, HTTPException, Request, Response, Depends, status
from sqlalchemy.orm import Session

from app.auth.auth_provider import get_auth_provider
from app.services.jwt_manager import verify_session_cookie, create_session_cookie
from app.auth.dependencies import get_current_user, require_permission
from typing import List
from app.databases.users import SessionLocal
from app.models.users import LocalUser, UserProfile
from app.auth.password_utils import hash_password, verify_password
from app.services.profile_manager import ensure_user_profile
from app.schemas.users import MessageResponse,UserListItemSchema, MeResponse, ProfileResponse, AuthStatusResponse
import app.schemas.auth

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------
# LOGIN / LOGOUT / SESSION ROUTES
# ---------------------------------------------------------

@router.post("/login", response_model=MessageResponse)
def login(payload: app.schemas.auth.LoginRequest, response: Response):
    provider = get_auth_provider()

    # Authenticate using provider (local, LDAP, OIDC)
    result = provider.authenticate(payload.username, payload.password)
    if not result:
        # Avoid leaking whether username or password was wrong
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Ensure profile exists + update last_login
    ensure_user_profile(
        username=result["username"],
        full_name=result.get("full_name"),
        email=result.get("email")
    )

    # Create session cookie
    session = create_session_cookie(result)

    response.set_cookie(
        key="access_token",
        value=session["access_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=60 * 60 * 24,  # 24 hours
        path="/"
    )

    return MessageResponse(
        message="Login successful",
        username=result["username"],
        roles=result.get("roles", [])
    )


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True,
        samesite="strict"
    )
    return MessageResponse(message="Logged out successfully")



@router.get("/me", response_model=MeResponse)
def me(user = Depends(get_current_user)):
    return MeResponse(
        username=user["username"],
        roles=user.get("roles", []),
        provider=user.get("provider", "local")
    )


@router.post("/refresh", response_model=MessageResponse)
def refresh(request: Request, response: Response):
    user = verify_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = create_session_cookie(user)

    response.set_cookie(
        key="access_token",
        value=session["access_token"],
        httponly=True,
        secure=True,
        samesite="strict"
    )

    return MessageResponse(
        message="Session refreshed",
        username=user["username"]
    )



@router.get("/verify", response_model=AuthStatusResponse)
def verify(user = Depends(get_current_user)):
    return AuthStatusResponse(
        authenticated=True,
        user=user
    )

# Change Password Self Service
@router.post("/change-password", response_model=MessageResponse)
def change_password(
    old_password: str,
    new_password: str,
    user = Depends(get_current_user)
):
    db = SessionLocal()

    target = db.query(LocalUser).filter(LocalUser.username == user["username"]).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(old_password, target.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    target.password_hash = hash_password(new_password)
    db.commit()

    return MessageResponse(message="Password changed successfully", username=user["username"])


# ---------------------------------------------------------
# ADMIN‑ONLY LOCAL USER MANAGEMENT ROUTES
# ---------------------------------------------------------

@router.post("/add-user", response_model=MessageResponse)
def add_user(
    username: str,
    password: str,
    roles: str,
    full_name: str = None,
    email: str = None,
    timezone: str = "Australia/Perth",
    language: str = "en",
    theme: str = "light",
    user = Depends(require_permission("manage_users"))
):
    db: Session = SessionLocal()

    # Prevent recreating bootstrap admin
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot recreate bootstrap admin")

    # Check if user already exists
    existing = db.query(LocalUser).filter(LocalUser.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # Validate roles
    from config.permissions_loader import PERMISSIONS
    valid_roles = PERMISSIONS.keys()

    for r in roles.split(","):
        if r not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role: {r}")

    # Create user + profile atomically
    try:
        new_user = LocalUser(
            username=username,
            password_hash=hash_password(password),
            roles=roles
        )

        new_profile = UserProfile(
            username=username,
            full_name=full_name,
            email=email,
            timezone=timezone,
            language=language,
            theme=theme
        )

        db.add(new_user)
        db.add(new_profile)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")

    return MessageResponse( message="User created", username=username, roles=roles.split(",") )


@router.post("/update-user-roles", response_model=MessageResponse)
def update_user_roles(
    username: str,
    roles: str,
    user = Depends(require_permission("manage_users"))
):
    db: Session = SessionLocal()

    target = db.query(LocalUser).filter(LocalUser.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent modifying bootstrap admin
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot modify bootstrap admin roles")

    # Validate roles
    from config.permissions_loader import PERMISSIONS
    valid_roles = PERMISSIONS.keys()

    for r in roles.split(","):
        if r not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role: {r}")

    target.roles = roles
    db.commit()

    return MessageResponse( message="Roles updated", username=username, roles=roles.split(",") )



@router.get("/list-users", response_model=List[UserListItemSchema])
def list_users(user = Depends(require_permission("manage_users"))):
    db: Session = SessionLocal()

    # Load all local users (auth table)
    local_users = {u.username: u for u in db.query(LocalUser).all()}

    # Load all profiles (includes LDAP/OIDC users who logged in)
    profiles = db.query(UserProfile).all()

    result: List[UserListItemSchema] = []

    for p in profiles:
        local = local_users.get(p.username)

        result.append(
            UserListItemSchema(
                username=p.username,
                provider="local" if local else "external",
                roles=local.roles.split(",") if local and local.roles else [],
                is_active=local.is_active if local else True,
                full_name=p.full_name,
                email=p.email,
                timezone=p.timezone,
                language=p.language,
                theme=p.theme,
                last_login=p.last_login,  # Pydantic handles datetime serialization
            )
        )

    return result


@router.delete("/delete-user", response_model=MessageResponse)
def delete_user(
    username: str,
    user = Depends(require_permission("manage_users"))
):
    db: Session = SessionLocal()

    # Prevent deleting yourself
    if username == user["username"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    # Prevent deleting bootstrap admin
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete bootstrap admin")

    target = db.query(LocalUser).filter(LocalUser.username == username).first()
    profile = db.query(UserProfile).filter(UserProfile.username == username).first()

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Delete auth record
        db.delete(target)

        # Delete profile if exists
        if profile:
            db.delete(profile)

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete user")

    return MessageResponse( message="User deleted", username=username )


@router.post("/disable-user", response_model=MessageResponse)
def disable_user(
    username: str,
    user = Depends(require_permission("manage_users"))
):
    db: Session = SessionLocal()

    target = db.query(LocalUser).filter(LocalUser.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot disable bootstrap admin")

    target.is_active = False
    db.commit()

    return MessageResponse(message="User disabled", username=username)

@router.post("/enable-user", response_model=MessageResponse)
def enable_user(
    username: str,
    user = Depends(require_permission("manage_users"))
):
    db: Session = SessionLocal()

    target = db.query(LocalUser).filter(LocalUser.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = True
    db.commit()

    return MessageResponse(message="User enabled", username=username)


# ---------------------------------------------------------
# PROFILE Management
# ---------------------------------------------------------
@router.get("/get-profile", response_model=ProfileResponse)
def get_profile(user = Depends(get_current_user)):
    db = SessionLocal()
    profile = db.query(UserProfile).filter(UserProfile.username == user["username"]).first()

    return ProfileResponse(
        username=profile.username,
        full_name=profile.full_name,
        email=profile.email,
        timezone=profile.timezone,
        language=profile.language,
        theme=profile.theme,
        last_login=profile.last_login
    )

@router.post("/update-profile", response_model=MessageResponse)
def admin_update_profile(
    username: str,
    full_name: str = None,
    email: str = None,
    timezone: str = None,
    language: str = None,
    theme: str = None,
    user = Depends(require_permission("manage_users"))
):
    db: Session = SessionLocal()

    profile = db.query(UserProfile).filter(UserProfile.username == username).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if full_name is not None:
        profile.full_name = full_name
    if email is not None:
        profile.email = email
    if timezone is not None:
        profile.timezone = timezone
    if language is not None:
        profile.language = language
    if theme is not None:
        profile.theme = theme

    db.commit()

    return MessageResponse(message="Profile updated", username=user["username"])


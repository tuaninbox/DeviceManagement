from sqlalchemy.orm import Session
from app.auth.base_auth import AuthProvider
from app.auth.password_utils import verify_password
from app.models.users import LocalUser
from app.databases.users import SessionLocal

class LocalAuth(AuthProvider):
    def authenticate(self, username: str, password: str):
        db: Session = SessionLocal()

        user = db.query(LocalUser).filter(LocalUser.username == username).first()
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        roles = user.roles.split(",") if user.roles else ["user"]

        return { 
            "username": user.username,
            "roles": user.roles.split(","),
            "provider": "local"
            }


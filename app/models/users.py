from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone
from app.databases.users import Base

class LocalUser(Base):
    __tablename__ = "local_users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    roles = Column(String)  # comma-separated
    is_active = Column(Boolean, default=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)

    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)

    timezone = Column(String, default="Australia/Perth")
    language = Column(String, default="en")
    theme = Column(String, default="light")

    last_login = Column(DateTime(timezone=True), default=None)
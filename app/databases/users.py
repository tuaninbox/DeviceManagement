from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.config_loader import get_users_db_path

# Load the path from config.ini
db_path = get_users_db_path()

# Build a proper SQLAlchemy SQLite URL
USERS_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    USERS_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

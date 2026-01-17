from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.config_loader import get_jobs_db_path

# Load the path from config.ini
db_path = get_jobs_db_path()

# Build a proper SQLAlchemy SQLite URL
JOBS_DB_URL = f"sqlite:///{db_path}"

jobs_engine = create_engine(
    JOBS_DB_URL,
    connect_args={"check_same_thread": False}
)

JobsSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=jobs_engine
)

JobsBase = declarative_base()

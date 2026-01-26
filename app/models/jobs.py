from sqlalchemy import Column, String, DateTime, Text
from app.databases.jobs import JobsBase
from datetime import datetime, timezone

class JobModel(JobsBase):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    category = Column(String)
    description = Column(String)
    status = Column(String)
    started_at = Column( DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) )
    finished_at = Column( DateTime(timezone=True), nullable = True )
    result = Column(Text)
    error = Column(Text)

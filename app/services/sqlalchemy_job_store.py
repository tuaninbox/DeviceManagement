import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.databases.jobs import JobsSessionLocal, jobs_engine, JobsBase
from app.models.jobs import JobModel
from .job_store import JobStore

# Ensure table exists
JobsBase.metadata.create_all(bind=jobs_engine)

class SQLAlchemyJobStore(JobStore):
    def create(self, job_id: str, data: Dict[str, Any]) -> None:
        db: Session = JobsSessionLocal()

        # JSON encode result if needed
        if isinstance(data.get("result"), (dict, list)):
            data["result"] = json.dumps(data["result"])

        job = JobModel(id=job_id, **data)
        db.add(job)
        db.commit()
        db.close()

    def update(self, job_id: str, data: Dict[str, Any]) -> None:
        db: Session = JobsSessionLocal()
        job = db.query(JobModel).filter(JobModel.id == job_id).first()

        if job:
            for k, v in data.items():
                # JSON encode dict/list before saving
                if k == "result" and isinstance(v, (dict, list)):
                    v = json.dumps(v)
                setattr(job, k, v)

            db.commit()

        db.close()

    def get(self, job_id: str) -> Optional[JobModel]:
        db: Session = JobsSessionLocal()
        job = db.query(JobModel).filter(JobModel.id == job_id).first()
        db.close()
        return job

    def list(self) -> List[JobModel]:
        db: Session = JobsSessionLocal()
        jobs = db.query(JobModel).order_by(JobModel.started_at.desc()).all()
        db.close()
        return jobs

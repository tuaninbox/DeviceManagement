from fastapi import APIRouter, HTTPException
from app.services.job_manager import job_store

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/")
def list_jobs():
    return job_store.list()

@router.get("/{job_id}")
def get_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# from fastapi import APIRouter, HTTPException
# from app.services.job_manager import JOB_STORE

# router = APIRouter(prefix="/jobs", tags=["jobs"])


# @router.get("/")
# def list_jobs():
#     """
#     Return all background jobs, newest first.
#     """
#     jobs = list(JOB_STORE.values())
#     jobs.sort(key=lambda j: j.get("started_at") or j.get("id"), reverse=True)
#     return jobs


# @router.get("/{job_id}")
# def get_job(job_id: str):
#     """
#     Return a single job by ID.
#     """
#     job = JOB_STORE.get(job_id)
#     if not job:
#         raise HTTPException(status_code=404, detail="Job not found")
#     return job

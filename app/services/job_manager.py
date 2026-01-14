import uuid
from datetime import datetime
from .sqlite_job_store import SQLiteJobStore
from config.config_loader import get_jobs_db_path

job_store = SQLiteJobStore(get_jobs_db_path())

def create_job(description: str, category: str):
    job_id = str(uuid.uuid4())
    job_store.create(job_id, {
        "category": category,
        "description": description,
        "status": "queued",
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
    })
    return job_id

def update_job(job_id: str, **fields):
    job_store.update(job_id, fields)


# import uuid
# from datetime import datetime

# # In-memory job store
# JOB_STORE = {}

# def create_job(description: str, category: str):
#     job_id = str(uuid.uuid4())
#     JOB_STORE[job_id] = {
#         "id": job_id,
#         "category": category,
#         "description": description,
#         "status": "queued",
#         "started_at": None,
#         "finished_at": None,
#         "result": None,
#         "error": None,
#     }
#     return job_id


# def update_job(job_id: str, **fields):
#     if job_id in JOB_STORE:
#         JOB_STORE[job_id].update(fields)

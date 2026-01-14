import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from .job_store import JobStore

class SQLiteJobStore(JobStore):
    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                category TEXT,
                description TEXT,
                status TEXT,
                started_at TEXT,
                finished_at TEXT,
                result TEXT,
                error TEXT
            )
        """)
        conn.commit()
        conn.close()

    def create(self, job_id: str, data: Dict[str, Any]) -> None:
        conn = self._connect()
        conn.execute("""
            INSERT INTO jobs (id, category, description, status, started_at, finished_at, result, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            data.get("category"),
            data.get("description"),
            data.get("status"),
            data.get("started_at"),
            data.get("finished_at"),
            data.get("result"),
            data.get("error"),
        ))
        conn.commit()
        conn.close()

    def update(self, job_id: str, data: Dict[str, Any]) -> None:
        if not data:
            return

        fields = ", ".join([f"{k}=?" for k in data.keys()])
        values = list(data.values())
        values.append(job_id)

        conn = self._connect()
        conn.execute(f"UPDATE jobs SET {fields} WHERE id=?", values)
        conn.commit()
        conn.close()

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": row[0],
            "category": row[1],
            "description": row[2],
            "status": row[3],
            "started_at": row[4],
            "finished_at": row[5],
            "result": row[6],
            "error": row[7],
        }

    def list(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.execute("SELECT * FROM jobs ORDER BY started_at DESC")
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "category": row[1],
                "description": row[2],
                "status": row[3],
                "started_at": row[4],
                "finished_at": row[5],
                "result": row[6],
                "error": row[7],
            }
            for row in rows
        ]

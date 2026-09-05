from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

from db import database

JobStatus = Literal["pending", "processing", "completed", "failed"]
JobFormat = Literal["txt", "epub", "pdf"]


@dataclass
class Job:
    id: str
    format: JobFormat
    status: JobStatus
    original_filename: str
    input_path: str
    output_path: Optional[str]
    total_blocks: Optional[int]
    translated_blocks: int
    error_message: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def _from_row(cls, row) -> "Job":
        return cls(
            id=row["id"],
            format=row["format"],
            status=row["status"],
            original_filename=row["original_filename"],
            input_path=row["input_path"],
            output_path=row["output_path"],
            total_blocks=row["total_blocks"],
            translated_blocks=row["translated_blocks"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(
    job_id: str, format: JobFormat, original_filename: str, input_path: str
) -> None:
    now = _now()
    with database.connection() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, format, status, original_filename, input_path,
                output_path, total_blocks, translated_blocks, error_message,
                created_at, updated_at
            ) VALUES (?, ?, 'pending', ?, ?, NULL, NULL, 0, NULL, ?, ?)
            """,
            (job_id, format, original_filename, input_path, now, now),
        )


def get_job(job_id: str) -> Optional[Job]:
    with database.connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return Job._from_row(row) if row else None


def mark_processing(job_id: str) -> None:
    with database.connection() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'processing', updated_at = ? WHERE id = ?",
            (_now(), job_id),
        )


def update_progress(job_id: str, translated_blocks: int, total_blocks: int) -> None:
    with database.connection() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET translated_blocks = ?, total_blocks = ?, updated_at = ?
            WHERE id = ?
            """,
            (translated_blocks, total_blocks, _now(), job_id),
        )


def mark_completed(job_id: str, output_path: str) -> None:
    with database.connection() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'completed', output_path = ?, updated_at = ? WHERE id = ?",
            (output_path, _now(), job_id),
        )


def mark_failed(job_id: str, error_message: str) -> None:
    with database.connection() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
            (error_message, _now(), job_id),
        )

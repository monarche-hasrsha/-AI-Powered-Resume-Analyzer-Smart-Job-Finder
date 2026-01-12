from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

DEFAULT_DB_PATH = os.getenv("APP_DB_PATH", "data/app.db")


def _ensure_db_dir(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    _ensure_db_dir(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db_path(db_path: str | None = None) -> str:
    return db_path or DEFAULT_DB_PATH


def init_db(db_path: str | None = None) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                link TEXT,
                posted TEXT,
                schedule_type TEXT,
                source TEXT,
                match_reason TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_hash TEXT NOT NULL UNIQUE,
                summary TEXT,
                raw_text TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS email_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT,
                subject TEXT,
                sender TEXT,
                snippet TEXT,
                last_message_at TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER,
                job_id INTEGER,
                recruiter_id INTEGER,
                subject TEXT,
                body TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                FOREIGN KEY(thread_id) REFERENCES email_threads(id),
                FOREIGN KEY(job_id) REFERENCES jobs(id),
                FOREIGN KEY(recruiter_id) REFERENCES recruiters(id)
            );

            CREATE TABLE IF NOT EXISTS recruiters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                company TEXT,
                title TEXT,
                profile_url TEXT,
                source_url TEXT,
                work_email TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                details_json TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
    conn.close()


def _now() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def get_db_status(db_path: str | None = None) -> dict:
    conn = get_connection(db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [row["name"] for row in tables]
    jobs_count = conn.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()["count"]
    last_insert = conn.execute(
        "SELECT created_at FROM jobs ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return {
        "db_path": get_db_path(db_path),
        "tables": table_names,
        "jobs_count": jobs_count,
        "last_job_insert": last_insert["created_at"] if last_insert else None,
    }


def _job_fingerprint(job: dict) -> str:
    raw = "|".join(
        [
            str(job.get("title", "")).strip().lower(),
            str(job.get("company", "")).strip().lower(),
            str(job.get("link", "") or job.get("url", "")).strip().lower(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_audit_event(
    conn: sqlite3.Connection,
    event_type: str,
    entity_type: str,
    entity_id: int | None,
    details: dict | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (event_type, entity_type, entity_id, details_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            event_type,
            entity_type,
            entity_id,
            json.dumps(details or {}),
            _now(),
        ),
    )


def upsert_jobs(
    jobs: Iterable[dict],
    source: str,
    db_path: str | None = None,
) -> tuple[int, int]:
    conn = get_connection(db_path)
    created = 0
    updated = 0
    with conn:
        for job in jobs:
            fingerprint = _job_fingerprint(job)
            existing = conn.execute(
                "SELECT id FROM jobs WHERE fingerprint = ?",
                (fingerprint,),
            ).fetchone()

            payload = {
                "fingerprint": fingerprint,
                "title": job.get("title") or "Unknown",
                "company": job.get("company"),
                "location": job.get("location"),
                "link": job.get("link") or job.get("url"),
                "posted": job.get("posted"),
                "schedule_type": job.get("schedule_type"),
                "source": source,
                "match_reason": job.get("match_reason"),
                "updated_at": _now(),
            }

            if existing:
                conn.execute(
                    """
                    UPDATE jobs
                    SET location = :location,
                        link = :link,
                        posted = :posted,
                        schedule_type = :schedule_type,
                        source = :source,
                        match_reason = :match_reason,
                        updated_at = :updated_at
                    WHERE fingerprint = :fingerprint
                    """,
                    payload,
                )
                updated += 1
                record_audit_event(
                    conn,
                    "job_updated",
                    "jobs",
                    existing["id"],
                    {"source": source},
                )
            else:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        fingerprint,
                        title,
                        company,
                        location,
                        link,
                        posted,
                        schedule_type,
                        source,
                        match_reason,
                        status,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :fingerprint,
                        :title,
                        :company,
                        :location,
                        :link,
                        :posted,
                        :schedule_type,
                        :source,
                        :match_reason,
                        'new',
                        :created_at,
                        :updated_at
                    )
                    """,
                    {**payload, "created_at": _now()},
                )
                created += 1
                job_id = conn.execute(
                    "SELECT id FROM jobs WHERE fingerprint = ?",
                    (fingerprint,),
                ).fetchone()["id"]
                record_audit_event(
                    conn,
                    "job_created",
                    "jobs",
                    job_id,
                    {"source": source},
                )

    conn.close()
    return created, updated


def list_jobs(
    status: Optional[str] = None,
    limit: int = 100,
    db_path: str | None = None,
) -> list[dict]:
    conn = get_connection(db_path)
    query = "SELECT * FROM jobs"
    params: tuple = ()
    if status and status != "all":
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY updated_at DESC LIMIT ?"
    params = (*params, limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_job_status(
    job_id: int,
    status: str,
    db_path: str | None = None,
) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), job_id),
        )
        record_audit_event(
            conn,
            "job_status_updated",
            "jobs",
            job_id,
            {"status": status},
        )
    conn.close()

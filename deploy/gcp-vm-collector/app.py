from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", "/var/lib/cosyvoice-usage/events.db"))
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
RETENTION_DAYS = max(1, int(os.environ.get("RETENTION_DAYS", "180")))
ALLOWED_EVENTS = {"reporting_enabled", "synthesis_finished", "quality_feedback"}

app = FastAPI(
    title="CosyVoice2 Korean SFT Usage Collector",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


class ClientMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: str | None = Field(default=None, max_length=32)
    os: str | None = Field(default=None, max_length=32)
    python: str | None = Field(default=None, max_length=16)
    gpu: str | None = Field(default=None, max_length=120)
    vram_gib: float | None = None
    cuda_available: bool | None = None


class EventPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: Literal[1]
    event_id: str = Field(min_length=1, max_length=64)
    event: str = Field(min_length=1, max_length=40)
    timestamp: int
    install_id: str = Field(min_length=1, max_length=64)
    participant_id: str | None = Field(default=None, max_length=100)
    client: ClientMetadata = Field(default_factory=ClientMetadata)
    properties: dict[str, Any] = Field(default_factory=dict)


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with closing(connect()) as connection:
        connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS usage_events (
              event_id TEXT PRIMARY KEY,
              received_at INTEGER NOT NULL,
              event_time INTEGER NOT NULL,
              event_name TEXT NOT NULL,
              install_id TEXT NOT NULL,
              participant_id TEXT,
              client_version TEXT,
              operating_system TEXT,
              python_version TEXT,
              gpu TEXT,
              vram_gib REAL,
              cuda_available INTEGER,
              success INTEGER,
              elapsed_sec REAL,
              duration_sec REAL,
              text_chars_bucket TEXT,
              error_type TEXT,
              feedback_score INTEGER,
              feedback_category TEXT,
              feedback_comment TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_usage_events_time ON usage_events(received_at);
            CREATE INDEX IF NOT EXISTS idx_usage_events_install ON usage_events(install_id);
            CREATE INDEX IF NOT EXISTS idx_usage_events_name ON usage_events(event_name);
            """
        )
        connection.execute(
            "DELETE FROM usage_events WHERE received_at < ?",
            (int(time.time()) - RETENTION_DAYS * 86_400,),
        )
        connection.commit()


@app.on_event("startup")
def startup() -> None:
    initialize_database()


def optional_text(value: Any, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized[:max_length] or None


def optional_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def require_admin(authorization: str | None) -> None:
    if not ADMIN_TOKEN or authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/events", status_code=status.HTTP_202_ACCEPTED)
def ingest(payload: EventPayload) -> dict[str, bool]:
    if payload.event not in ALLOWED_EVENTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported event")
    properties = payload.properties
    success = properties.get("success")
    success_value = 1 if success is True else 0 if success is False else None
    with closing(connect()) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO usage_events (
              event_id, received_at, event_time, event_name, install_id, participant_id,
              client_version, operating_system, python_version, gpu, vram_gib, cuda_available,
              success, elapsed_sec, duration_sec, text_chars_bucket, error_type,
              feedback_score, feedback_category, feedback_comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.event_id,
                int(time.time()),
                payload.timestamp,
                payload.event,
                payload.install_id,
                optional_text(payload.participant_id, 100),
                payload.client.version,
                payload.client.os,
                payload.client.python,
                payload.client.gpu,
                payload.client.vram_gib,
                int(payload.client.cuda_available)
                if payload.client.cuda_available is not None
                else None,
                success_value,
                optional_number(properties.get("elapsed_sec")),
                optional_number(properties.get("duration_sec")),
                optional_text(properties.get("text_chars_bucket"), 16),
                optional_text(properties.get("error_type"), 80),
                optional_number(properties.get("score")),
                optional_text(properties.get("category"), 40),
                optional_text(properties.get("comment"), 500),
            ),
        )
        connection.commit()
    return {"accepted": True}


@app.get("/v1/stats")
def stats(authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_admin(authorization)
    with closing(connect()) as connection:
        summary = connection.execute(
            """
            SELECT
              COUNT(DISTINCT install_id) AS installations,
              COUNT(DISTINCT CASE WHEN participant_id IS NOT NULL THEN participant_id END)
                AS identified_participants,
              SUM(CASE WHEN event_name = 'synthesis_finished' THEN 1 ELSE 0 END) AS syntheses,
              ROUND(100.0 * AVG(CASE WHEN event_name = 'synthesis_finished' THEN success END), 2)
                AS success_rate_pct,
              ROUND(AVG(CASE WHEN duration_sec > 0 THEN elapsed_sec / duration_sec END), 3)
                AS average_rtf,
              ROUND(AVG(CASE WHEN event_name = 'quality_feedback' THEN feedback_score END), 2)
                AS feedback_average
            FROM usage_events
            """
        ).fetchone()
        gpus = connection.execute(
            """
            SELECT gpu, COUNT(DISTINCT install_id) AS installations
            FROM usage_events WHERE gpu IS NOT NULL
            GROUP BY gpu ORDER BY installations DESC LIMIT 20
            """
        ).fetchall()
        errors = connection.execute(
            """
            SELECT error_type, COUNT(*) AS occurrences
            FROM usage_events WHERE success = 0 AND error_type IS NOT NULL
            GROUP BY error_type ORDER BY occurrences DESC LIMIT 20
            """
        ).fetchall()
    return {
        "summary": dict(summary),
        "gpus": [dict(row) for row in gpus],
        "errors": [dict(row) for row in errors],
    }


@app.get("/v1/participants")
def participants(authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_admin(authorization)
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT
              COALESCE(participant_id, 'anonymous:' || SUBSTR(install_id, -8)) AS participant,
              MAX(gpu) AS gpu,
              COUNT(CASE WHEN event_name = 'synthesis_finished' THEN 1 END) AS syntheses,
              ROUND(100.0 * AVG(CASE WHEN event_name = 'synthesis_finished' THEN success END), 2)
                AS success_rate_pct,
              MAX(received_at) AS last_seen
            FROM usage_events
            GROUP BY install_id, participant_id
            ORDER BY last_seen DESC LIMIT 500
            """
        ).fetchall()
    return {"participants": [dict(row) for row in rows]}


@app.head("/v1/events")
def events_head() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)

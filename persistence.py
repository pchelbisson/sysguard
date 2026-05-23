"""SQLite persistence for SysGuard execution history and basic trends."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List


DB_FILE_MODE = 0o600


def validate_history_db_path(db_path: str, allowed_root: str = "data") -> Path:
    """Allow only relative database paths under allowed_root directory."""
    candidate = Path(db_path).expanduser()
    if candidate.is_absolute():
        raise ValueError("history_db_path must be a relative path inside the data directory")

    normalized = candidate.resolve(strict=False)
    root = Path(allowed_root).resolve(strict=False)

    try:
        normalized.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"history_db_path must stay under '{allowed_root}/' (got: {db_path})"
        ) from exc

    if normalized.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError("history_db_path must use a sqlite extension: .db/.sqlite/.sqlite3")

    return normalized


def _ensure_secure_db_file_permissions(db_file: Path) -> None:
    """Ensure sqlite database file is readable/writable only by owner."""
    if not db_file.exists():
        return
    os.chmod(db_file, DB_FILE_MODE)


def _connect(db_path: str) -> sqlite3.Connection:
    db_file = validate_history_db_path(db_path)
    if db_file.parent and not db_file.parent.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    _ensure_secure_db_file_permissions(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    """Create persistence schema if it does not exist."""
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at TEXT NOT NULL,
                summary_severity TEXT NOT NULL,
                exit_code INTEGER NOT NULL,
                checks_total INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS check_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                check_name TEXT NOT NULL,
                status TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                data_json TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_runs_generated_at ON runs(generated_at);
            CREATE INDEX IF NOT EXISTS idx_check_results_run_id ON check_results(run_id);
            CREATE INDEX IF NOT EXISTS idx_check_results_check_name ON check_results(check_name);
            """
        )


def save_run(report_document: Dict[str, Any], db_path: str) -> int:
    """Persist one SysGuard report document and return run id."""
    init_db(db_path)

    summary = report_document.get("summary", {})
    results = report_document.get("results", [])
    generated_at = str(report_document.get("generated_at") or datetime.now(timezone.utc).isoformat())

    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO runs (generated_at, summary_severity, exit_code, checks_total)
            VALUES (?, ?, ?, ?)
            """,
            (
                generated_at,
                str(summary.get("severity", "warning")),
                int(summary.get("exit_code", 1)),
                int(summary.get("checks_total", len(results))),
            ),
        )
        run_id = int(cursor.lastrowid)

        conn.executemany(
            """
            INSERT INTO check_results (run_id, check_name, status, severity, message, data_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    str(item.get("check_name", "unknown_check")),
                    str(item.get("status", "WARNING")),
                    str(item.get("severity", "warning")),
                    str(item.get("message", "")),
                    json.dumps(item.get("data", {}), ensure_ascii=False),
                )
                for item in results
            ],
        )

        return run_id


def query_disk_usage_trend(db_path: str, disk_path: str = "/", days: int = 7) -> List[Dict[str, Any]]:
    """Return disk usage history for `check_disk` over the last N days."""
    init_db(db_path)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT r.generated_at, cr.data_json
            FROM check_results cr
            JOIN runs r ON r.id = cr.run_id
            WHERE cr.check_name = 'check_disk' AND r.generated_at >= ?
            ORDER BY r.generated_at ASC
            """,
            (cutoff,),
        ).fetchall()

    trend = []
    for row in rows:
        data = json.loads(row["data_json"])
        if str(data.get("path")) != disk_path:
            continue
        percent = data.get("percent")
        if isinstance(percent, (int, float)):
            trend.append({"generated_at": row["generated_at"], "path": disk_path, "percent": float(percent)})

    return trend


def query_failures_count_trend(db_path: str, days: int = 7) -> List[Dict[str, Any]]:
    """Return daily count of warning and critical findings for the last N days."""
    init_db(db_path)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT substr(r.generated_at, 1, 10) AS day,
                   SUM(CASE WHEN cr.severity = 'warning' THEN 1 ELSE 0 END) AS warnings,
                   SUM(CASE WHEN cr.severity = 'critical' THEN 1 ELSE 0 END) AS criticals
            FROM check_results cr
            JOIN runs r ON r.id = cr.run_id
            WHERE r.generated_at >= ?
            GROUP BY day
            ORDER BY day ASC
            """,
            (cutoff,),
        ).fetchall()

    return [
        {
            "day": row["day"],
            "warnings": int(row["warnings"] or 0),
            "criticals": int(row["criticals"] or 0),
            "failures_total": int(row["warnings"] or 0) + int(row["criticals"] or 0),
        }
        for row in rows
    ]
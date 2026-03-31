"""Unified JSON report schema helpers for all health checks."""

from __future__ import annotations

from typing import Any, Dict


ALLOWED_STATUSES = {"OK", "WARNING", "ERROR"}
STATUS_NORMALIZATION = {
    "INFO": "OK",
    "CRITICAL": "ERROR",
    "UNKNOWN": "WARNING",
}


def normalize_check_result(raw_result: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normalize arbitrary check payload into a stable single contract."""
    result = raw_result or {}

    check_name = str(result.get("check_name") or "unknown_check")
    raw_status = str(result.get("status") or "UNKNOWN").upper()
    status = STATUS_NORMALIZATION.get(raw_status, raw_status)
    if status not in ALLOWED_STATUSES:
        status = "WARNING"

    message = str(result.get("message") or "")

    # Backward compatibility: some checks still use `details`.
    data = result.get("data")
    if not isinstance(data, dict):
        details = result.get("details")
        data = details if isinstance(details, dict) else {}

    normalized = {
        "check_name": check_name,
        "status": status,
        "message": message,
        "data": data,
    }
    return normalized
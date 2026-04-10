"""Unified JSON report schema helpers for all health checks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


ALLOWED_STATUSES = {"OK", "WARNING", "ERROR"}
ALLOWED_SEVERITIES = {"ok", "warning", "critical"}
STATUS_NORMALIZATION = {
    "INFO": "OK",
    "CRITICAL": "ERROR",
    "UNKNOWN": "WARNING",
}
STATUS_TO_SEVERITY = {
    "OK": "ok",
    "WARNING": "warning",
    "ERROR": "critical",
}
SEVERITY_ORDER = {"ok": 0, "warning": 1, "critical": 2}
SEVERITY_TO_EXIT_CODE = {"ok": 0, "warning": 1, "critical": 2}
SCHEMA_VERSION = "1.0"


def normalize_check_result(raw_result: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normalize arbitrary check payload into a stable single contract."""
    result = raw_result or {}

    check_name = str(result.get("check_name") or "unknown_check")
    raw_status = str(result.get("status") or "UNKNOWN").upper()
    status = STATUS_NORMALIZATION.get(raw_status, raw_status)
    if status not in ALLOWED_STATUSES:
        status = "WARNING"
    severity = STATUS_TO_SEVERITY.get(status, "warning")
    if severity not in ALLOWED_SEVERITIES:
        severity = "warning"

    message = str(result.get("message") or "")

    # Backward compatibility: some checks still use `details`.
    data = result.get("data")
    if not isinstance(data, dict):
        details = result.get("details")
        data = details if isinstance(details, dict) else {}

    normalized = {
        "check_name": check_name,
        "status": status,
        "severity": severity,
        "message": message,
        "data": data,
    }
    return normalized

def get_report_severity(full_report: Iterable[Dict[str, Any]]) -> str:
    """Return max severity across normalized check results."""
    max_severity = "ok"
    for item in full_report:
        candidate = str(item.get("severity", "warning")).lower()
        if candidate not in ALLOWED_SEVERITIES:
            candidate = "warning"
        if SEVERITY_ORDER[candidate] > SEVERITY_ORDER[max_severity]:
            max_severity = candidate
    return max_severity


def get_exit_code_for_report(full_report: Iterable[Dict[str, Any]]) -> int:
    """Stable exit-code policy mapped to severity: ok=0, warning=1, critical=2."""
    severity = get_report_severity(full_report)
    return SEVERITY_TO_EXIT_CODE[severity]

def build_report_document(full_report: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build top-level machine-readable report document with explicit schema version."""
    normalized_results = [normalize_check_result(item) for item in full_report]
    aggregated_severity = get_report_severity(normalized_results)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "severity": aggregated_severity,
            "exit_code": SEVERITY_TO_EXIT_CODE[aggregated_severity],
            "checks_total": len(normalized_results),
        },
        "results": normalized_results,
    }
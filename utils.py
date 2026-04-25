import re
from typing import Any


SENSITIVE_FIELD_NAMES = ("password", "token", "secret", "api_key")
MASKED_VALUE = "***MASKED***"
INLINE_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*([\"']?)([^\s\"']+)\2"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,48}\b"),
)


def _is_sensitive_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(token in lowered for token in SENSITIVE_FIELD_NAMES)


def mask_string(value: str) -> str:
    """Mask likely secret-looking substrings inside arbitrary text."""
    masked = value
    for pattern in INLINE_SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)\\b(password"):
            masked = pattern.sub(lambda m: f"{m.group(1)}={MASKED_VALUE}", masked)
        else:
            masked = pattern.sub(MASKED_VALUE, masked)
    return masked


def mask_payload(payload: Any) -> Any:
    """
    Recursively mask sensitive values in payloads before logging/output.

    Rules:
    - values under sensitive keys are replaced with MASKED_VALUE;
    - string values are additionally scanned for inline secret patterns.
    """
    if isinstance(payload, dict):
        masked = {}
        for key, value in payload.items():
            if _is_sensitive_key(key):
                masked[key] = MASKED_VALUE
                continue
            masked[key] = mask_payload(value)
        return masked
    if isinstance(payload, list):
        return [mask_payload(item) for item in payload]
    if isinstance(payload, str):
        return mask_string(payload)
    return payload

def handle_error(report_dict, msg, is_critical):
    """Updates the report dictionary and logs the error."""
    
    if is_critical:
        report_dict["status"] = "ERROR"
        report_dict["data"]["is_critical_failure"] = True
    else:
        report_dict["status"] = "WARNING"
    report_dict["message"] = msg
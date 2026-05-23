# SysGuard — Linux System Health & Security Baseline CLI

SysGuard is a Python CLI utility for **read-only** Linux system checks.
It helps you run a quick host baseline for filesystem, system state, network, and basic security posture.

> ⚠️ Status: learning project / work in progress.  
> Not intended for production use without additional hardening and CI policy gates.

---

## Why this project exists

SysGuard is designed to practice practical DevOps skills:
- building maintainable CLI tooling,
- collecting system signals from Linux hosts,
- normalizing checks into a unified result format,
- preparing data for future reporting/automation.

---

## Current capabilities

`python3 main.py check` currently includes:

### System & runtime checks
- Python version compatibility check.
- Root execution detection (warning-only).
- `systemd` overall state check.

### Filesystem checks
- Disk usage threshold check.
- Directory checks (exists/type/readable + critical flag).
- Mount-point checks (with critical flag).
- LVM free space check (when tools are available).

### Network checks
- TCP port checks against configured host/ports.

### Security baseline checks (read-only)
- SSH hardening config checks:
  - `PermitRootLogin`
  - `PasswordAuthentication`
  - custom SSH `Port`
- Sensitive file permission checks (`/etc/shadow`, `/etc/passwd`).
- Firewall status check (UFW with iptables fallback logic).
- fail2ban availability/running status.
- Autostart/persistence hygiene: world-writable entries in systemd/cron paths.
- SELinux / AppArmor status detection.
- Simple regex-based secrets detection in configurable read-only paths.

### Logging & result format
- Rotating logs + console logs.
- Console logs are emitted to `stderr`; file logs are written with rotation.
- Each check returns a unified dictionary-like structure for aggregation.
- SQLite execution history persistence:
  - each `check` run is saved into `runs` and `check_results` tables,
  - basic trend query helpers are available for disk usage and failures count.
- Top-level JSON report contract now includes:
  - `schema_version` (currently `1.0`)
  - `generated_at` (UTC ISO-8601 timestamp)
  - `summary` (`severity`, `exit_code`, `checks_total`)
  - `results` (array of check results)
- Each check result uses a **single JSON contract**:
  - `check_name` (string)
  - `status` (`OK` / `WARNING` / `ERROR`)
  - `severity` (`ok` / `warning` / `critical`)
  - `message` (string)
  - `data` (object with check-specific payload)

Example top-level report:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-04-09T12:00:00+00:00",
  "summary": {
    "severity": "ok",
    "exit_code": 0,
    "checks_total": 1
  },
  "results": [
    {
      "check_name": "check_disk",
      "status": "OK",
      "severity": "ok",
      "message": "Disk space on / is within limits",
      "data": {
        "path": "/",
        "used_gb": 20,
        "total_gb": 100,
        "percent": 20.0
      }
    }
  ]
}
```

---

## Exit codes

- `0` — aggregate severity is `ok`.
- `1` — aggregate severity is `warning`.
- `2` — aggregate severity is `critical`.

---

## Configuration

Default config file: `config.json` (or pass custom path via `--config`).

Example:

```json
{
  "directories": [
    {"path": "/var/log", "critical": false},
    {"path": "/etc", "critical": true}
  ],
  "mounts": [
    {"path": "/", "critical": true}
  ],
  "disk_paths": ["/"],
  "disk_threshold": 85,
  "required_ports": [22, 80, 443],
  "check_hosts": ["8.8.8.8"],
  "lvm_threshold_gb": 1.0,
  "ssh_config_path": "/etc/ssh/sshd_config",
  "secrets_scan_paths": ["./configs", "./.env"],
  "api_key_env": "SYSGUARD_API_KEY",
  "history_db_path": "./data/sysguard_history.db"
}
```

Notes:
- For network checks, only the first host from `check_hosts` is used currently.
- `ssh_config_path` is optional; when omitted, SysGuard tries standard `sshd_config` paths
- `secrets_scan_paths` is optional; when empty, the secrets check returns a warning.
- Sensitive values are loaded from environment variables only via `*_env` keys.
- `history_db_path` controls where SQLite run history is stored (default: `data/sysguard_history.db`).
  For security hardening, use a relative path under `data/` with a SQLite extension (`.db`, `.sqlite`, `.sqlite3`).
  Example: `api_key_env: "SYSGUARD_API_KEY"` injects the runtime value into `api_key`.
  Plaintext keys (`password`, `token`, `secret`, `api_key`) in `config.json` are forbidden.
  If such keys are present, config loading fails and those values are not used.
  This keeps plaintext credentials out of versioned config files.

---

## Usage

```bash
# Run checks with default config.json
python3 main.py check
```

```bash
# Save machine-readable JSON report to a file (clean terminal output)
python3 main.py check --output ./reports/latest.json
```

```bash
# Hide JSON output in stdout (keep logs in stderr/file)
python3 main.py check --quiet
```

```bash
# Run checks with a custom config file
python3 main.py --config /path/to/custom.json check
```

```bash
# Help
python3 main.py --help
```

---

## Testing

```bash
pytest -q
```

---

## Roadmap focus (Phase 2)

The current phase focuses on:
- policy-driven checks,
- machine-readable reporting improvements,
- secrets handling hygiene,
- quality gates for check schema and smoke e2e runs.

See details in [`ROADMAP.md`](./ROADMAP.md).

---

## Disclaimer

This repository is part of a DevOps learning journey.  
Feedback, issues, and suggestions are welcome.

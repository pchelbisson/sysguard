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

### Logging & result format
- Rotating logs + console logs.
- Each check returns a unified dictionary-like structure for aggregation.

---

## Exit codes

- `0` — no `ERROR` checks.
- `1` — one or more checks returned `ERROR` (or critical failure path).

---

## Exit codes

- `0` — no `ERROR` checks.
- `1` — one or more checks returned `ERROR` (or critical failure path).

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
  "ssh_config_path": "/etc/ssh/sshd_config"
}
```

Notes:
- For network checks, only the first host from `check_hosts` is used currently.
- `ssh_config_path` is optional; when omitted, SysGuard tries standard `sshd_config` paths

---

## Usage

```bash
# Run checks with default config.json
python3 main.py check
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

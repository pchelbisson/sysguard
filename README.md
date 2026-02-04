## SysGuard — System Health Check CLI (Work in Progress)
SysGuard is a simple Python CLI utility for basic Linux system health checks.

### ⚠️ Work in Progress
This project is under active development and is created as a learning project.
It is not intended for production use (yet).

---

### 🎯 Project Goals

* Learn how to build a Python CLI tool
* Practice system checks similar to real DevOps tasks
* Work with Linux, systemd, disk usage, and permissions
* Improve Python structure, readability, and CLI UX

This is my first project using Python, and I am learning while building it.

---

### 🔍 What SysGuard Does
Currently, the check command performs:
* ✅ Python version check (Python 3.8+)
* ⚠️ Root privilege detection (warning if not root)
* 💽 Disk usage check (alerts if usage > threshold)
* 📁 Directory checks:
    * existence
    * directory type
    * read permissions
    * critical flag
* ⚙️ systemd status check (systemctl is-system-running)
* 📦 LVM volume group free space check
* 📍 Mount point checks (with critical flag support)
* 🌐 Network port availability (TCP)
* 📝 Rotating file logs + console output

Each check returns a unified dictionary format for future JSON reporting.

Exit codes:
* 0 — all checks passed
* 1 — one or more checks failed (or critical failure)

---

### 🧰 Technologies & Libraries Used
Standard Python libraries only:
* argparse — CLI arguments
* sys — exit codes, version info
* os — permissions, UID checks
* pathlib — filesystem paths
* shutil — disk usage
* subprocess — systemd interaction
* socket — network connectivity and TCP port scanning
* json — configuration file parsing and data management
* logging — structured event tracking and status reporting
No external dependencies.

---

### ⚙️ Configuration

Parameters are configured via `config.json` (or custom path with `--config`):

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
  "lvm_threshold_gb": 1.0
}
```

---

### ▶️ Usage

```bash
# Default config (config.json)
python3 main.py check
```

```bash
# Custom config file
python3 main.py --config /path/to/custom.json check
```

```bash
#Help
python3 main.py --help
```

---

### 🧪 Testing
Basic pytest coverage (I plan to add more tests in the future):  
```bash
pytest test_sysguard.py -v
```
---

### 🚧 Work in Progress
Planned improvements:
* JSON report output (`report.json`)
* Database integration(SQLite)
* Telegram/Webhook alerting
* Dockerization & CI/CD pipeline

---

### 📌 Disclaimer
This project is created for learning purposes as part of my DevOps journey.
Feedback and suggestions are welcome.

## SysGuard — System Health Check CLI (Work in Progress)
SysGuard is a simple Python CLI utility for basic Linux system health checks.

### ⚠️ Work in Progress
This project is under active development and is created as a learning project.
It is not intended for production use (yet).

---

### 🎯 Project Goals

* Learn how to build a Python CLI too
* Practice system checks similar to real DevOps tasks
* Work with Linux, systemd, disk usage, and permissions
* Improve Python structure, readability, and CLI UX
This is my first project using Python, and I am learning while building it.

---

### 🔍 What SysGuard Does
Currently, the check command performs:
* ✅ Python version check (Python 3.8+)
* ⚠️ Root privilege detection (warning if not root)
* 💽 Disk usage check (alerts if usage > 90%)
* 📁 Directory checks:
    * existence
    * directory type
    * read permissions
* ⚙️ systemd status check (systemctl is-system-running)
* 📦 LVM volume group free space check
* 📍 Mount point checks
* 🌐 Network port availability (TCP)
* 📝 All checks are logged using Python logging.
Each check prints a clear status and the tool exits with:
* 0 — all checks passed
* 1 — one or more checks failed

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

Some parameters are configured via config.json, for example:

* directories to check
* disk usage threshold
* network hosts and ports
This allows changing behavior without modifying the code.

---

### ▶️ Usage

```bash
python3 sysguard.py check
```

Help:
```bash
python3 sysguard.py --help
```

---

### 🚧 Work in Progress
Planned improvements:
* Database integration
* Better output formatting
* Config file support
* More system checks
* Packaging as a real CLI tool

---

### 📌 Disclaimer
This project is created for learning purposes as part of my DevOps journey.
Feedback and suggestions are welcome.

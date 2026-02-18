## 🚀 SysGuard: DevOps Learning Roadmap 2026

### 🟢 Phase 1: CLI Utility Fundamentals

- [x] **`Focus:`** Core logic and local system interaction.
- [x] **`Base Logic:`** Develop Python modules to monitor disk usage, systemd services, and OS versions.
- [x] **`Advanced Logging:`** Transition from print() to the logging module with structured levels (INFO, WARNING, ERROR) and file rotation.
- [x] **`External Configuration:`** Move thresholds and paths into a config.json or config.yaml file.
- [x] **`Network Audit:`** Checking open ports (SSH 2222, MySQL) and auditing network interfaces.
- [x] **`LVM Integration:`** Add a module for Logical Volume Manager (LVM) health checks (practicing subprocess and CLI parsing).
- [x] Standardization of the check structure (single interface)
- [x] Unified check result format (dict)
- [x] Log refactoring
- [x] main() refactoring
- [x] Pytest
- [x] Add --config /path

### 🟡 Phase 2: Data, Security Baseline & Reporting (Python for DevOps) (Current Stage)

- **`Focus:`** Turn the utility into a policy-driven system checker
- **`Security Baseline:`**
  - **✅ `Definitely try:`**
    - [x] **SSH hardening checks:**
      - `PermitRootLogin`
      - `PasswordAuthentication`
      - Custom SSH port
    - [x] **File permission checks:**
      - `/etc/shadow`
      - `/etc/passwd`
      - `/root`
    - [x] **Warning-only checks for root execution**
  - **🟡 `That would be nice`**
    - [x] **Firewall status check (ufw / firewalld)**
    - [x] **fail2ban status**
    - **SELinux / AppArmor status (read-only)**
  - **🔵`Optional`**
    - **Simple secrets detection (regex-based, read-only)**
- **`JSON Reporting:`**
  - **✅`Definitely try:`**
    - **Unified JSON report (machine-readable)**
    - **stdout → JSON, logs → file/stderr**
  - **🟡`That would be nice`**
    - **Report severity levels (ok / warning / critical)**
- **`Configuration & Secrets Handling:`**
  - **✅ `Definitely try:`**
    - Read sensitive values only from environment variables (local only)
    - No secrets in config.json
  - **🟡 `That would be nice:`**
    - Validation if required env vars are missing
- **`Persistence Layer:`** 
  - **🟡`That would be nice`**
    - **SQLite DB:**
      - store execution history
      - trend analysis (disk, failures)
  - **🔵`Optional`**
    - **Aggregation / basic stats**
- **🟡`Automated Alerting:`**
  - **`That would be nice`**
    - **Telegram / Webhook alerts on critical failures**
- **`Operational Scope:`**
  - **✅ `Definitely try:`**
    - Read-only checks only

### 🟠 Phase 3: Containerization & Automation (DevOps Core)
- **`Focus:`** Portability and CI/CD pipelines.
- **`Static Analysis (SAST):`** Integration of Bandit and Safety into the pipeline.
- **`Secret Scanning:`** Checking if you have accidentally forgotten your password or key in the code.
- **`Dockerization:`** Create a Dockerfile (optimized for size) to run SysGuard in an isolated container.
- **`CI/CD (Gitlab CI):`** Automate linting and unit testing for every git push.
- **`Ansible:`** Write playbooks to automate the deployment and configuration of SysGuard on multiple remote servers.
- **`Backup Command:`** Implementing the sysguard backup command for a MySQL database using xz compression and archive rotation.

### 🔴 Phase 4: Infrastructure as Code & Cloud
- **`Focus:`** Scaling and cloud-native services (Yandex Cloud).
- **`Terraform (IaC):`** Provision Virtual Machines and networks in the cloud using declarative code.
- **`Cloud Monitoring:`** Bridge SysGuard metrics with cloud-native monitoring services.

### 🟣 Phase 5: Orchestration & Observability
- **`Focus:`** Enterprise-grade high availability and visualization.
- **`K8s Deployment:`** Launch SysGuard as a CronJob or DaemonSet within a Kubernetes cluster.
- **`Helm Packaging:`** Create a Helm Chart for one-click installation in K8s.
- **`Observability Stack:`** Export data to Prometheus and visualize system health on a Grafana dashboard.
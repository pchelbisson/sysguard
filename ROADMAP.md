## 🚀 SysGuard: DevOps Learning Roadmap 2026

### 🟢 Phase 1: CLI Utility Fundamentals (Current Stage)

- [x] **`Focus:`** Core logic and local system interaction.
- [x] **`Base Logic:`** Develop Python modules to monitor disk usage, systemd services, and OS versions.
- [x] **`Advanced Logging:`** Transition from print() to the logging module with structured levels (INFO, WARNING, ERROR) and file rotation.
- [x] **`External Configuration:`** Move thresholds and paths into a config.json or config.yaml file.
- [ ] **`Network Audit:`** Checking open ports (SSH 2222, MySQL) and auditing network interfaces.
- [ ] **`LVM Integration:`** Add a module for Logical Volume Manager (LVM) health checks (practicing subprocess and CLI parsing).

### 🟡 Phase 2: Data & Networking (Python for DevOps)

**`Focus:`** Machine-readable data and remote notifications.
**`Backup Command:`** Implementing the sysguard backup command for a MySQL database using xz compression and archive rotation.
**`Security Hardening:`** Checking SSH configuration (disabling root login, custom port) and using RSA keys.
**`JSON Reporting:`** Generate structured reports for integration with third-party tools.
**`Persistence Layer:`** Implement an SQLite database to store history and track system performance trends.
**`Automated Alerting:`** Integrate Telegram API or Webhooks to send instant notifications on critical errors.

### 🟠 Phase 3: Containerization & Automation (DevOps Core)
**`Focus:`** Portability and CI/CD pipelines.
**`Dockerization:`** Create a Dockerfile (optimized for size) to run SysGuard in an isolated container.
**`CI/CD (Gitlab CI):`** Automate linting and unit testing for every git push.
**`Ansible:`** Write playbooks to automate the deployment and configuration of SysGuard on multiple remote servers.

### 🔴 Phase 4: Infrastructure as Code & Cloud
**`Focus:`** Scaling and cloud-native services (Yandex Cloud).
**`Terraform (IaC):`** Provision Virtual Machines and networks in the cloud using declarative code.
**`Cloud Monitoring:`** Bridge SysGuard metrics with cloud-native monitoring services.

### 🟣 Phase 5: Orchestration & Observability
**`Focus:`** Enterprise-grade high availability and visualization.
**`K8s Deployment:`** Launch SysGuard as a CronJob or DaemonSet within a Kubernetes cluster.
**`Helm Packaging:`** Create a Helm Chart for one-click installation in K8s.
**`Observability Stack:`** Export data to Prometheus and visualize system health on a Grafana dashboard.
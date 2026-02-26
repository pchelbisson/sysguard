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
    - [x] **Checking autostart and persistence (read-only)**
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
    - Explicit deny-list of keys: `password`, `token`, `secret`, `api_key`.
  - **Masking sensitive values ​​in logs/reports**
    - Universal helper `mask_value("abcd1234") -> "ab***34"`.
  - **🟡 `That would be nice:`**
    - Validation if required env vars are missing
- **`Persistence Layer:`** 
  - **🟡`That would be nice`**
    - **SQLite DB:**
      - store execution history
      - tables: `runs`, `check_results`.
      - trend analysis (disk, failures)
  - **🔵`Optional`**
    - **Aggregation / basic stats**
    - **CLI trend commands**
      - `sysguard history --last 20`
      - `sysguard trend --check disk_root --days 7`.
    - **Retention policy**
      - Automatically clear old records (`--retention-days`).
- **🟡`Automated Alerting:`**
  - **`That would be nice`**
    - **Telegram / Webhook alerts on critical failures**
- **Contract tests for the check-result structure**
  - **✅ `Definitely try:`**
    - Every check must return the same schema.
    - **Configuration tests and edge cases**
    - Broken JSON, empty lists, invalid thresholds.
    - **Smoke e2e CLI test**
    - Minimal run of `main.py check` on a test config.
- **`Operational Scope:`**
  - **✅ `Definitely try:`**
    - Read-only checks only

### 🟠 Phase 3: Containerization & Automation (DevOps Core)
- **`Focus:`**
  1. Repeatable build and run (local and in CI).
  2. Stable quality gate (tests + lint + security).
  3. Seamless delivery (container image + release artifacts).
  4. Preparing for multi-host deployment (Ansible).

#### Step A — Quality Gate to Docker
- Add CI stages:
  - unit tests (pytest)
  - style/lint (ruff/flake8)
  - security (bandit)
  - dependency scan (pip-audit/safety, if applicable)
  - Introduce policy:
  - merge is prohibited if tests/bandit fails.

#### Step B — Dockerization (after stable quality gate)
- **Multi-stage Dockerfile**:
  - build/test stage
  - runtime stage (`python:slim`)
- **Size and security optimization**:
  - non-root user
  - `PYTHONDONTWRITEBYTECODE=1`
  - `PYTHONUNBUFFERED=1`
  - minimal packages, clean apt cache
- **Container runtime contract**:
  - `ENTRYPOINT ["python", "main.py"]`
  - volume for reports/logs
  - documented environment variables.

#### Step C - CI/CD release workflow
- For each push in main: 
  - test + scan + build image. 
- On git tag: 
  - publish image (`:vX.Y.Z`, `:latest`) 
  - artifacts (json report attach schema, changelog).

#### Step D - Secret scanning and supply chain
- gitleaks/trufflehog in pre-commit and CI.
- SBOM (e.g., syft) + image scan (trivy).
- Container signature (cosign) — like stretch goal.

#### Step E - Ansible rollout
- Roles: 
  - `sysguard_install` 
  - `sysguard_config` 
  - `sysguard_schedule` (cron/systemd timer) 
  - Idempotency + `--check` mode. 
  - Support for inventory groups (dev/stage/prod).

#### CI pipeline target structure (example)
1. `validate` — format/lint
2. `test` — unit + coverage
3. `security` — bandit + secrets scan
4. `package` — docker build
5. `scan-image` — trivy
6. `publish` — only on tag/main according to rules

#### Phase 3 is considered complete when:
- There is a reproducible container run via `docker run`.
- The CI pipeline automatically checks tests, security, and builds.
- There is a documented release flow with image versioning.
- There is a minimal Ansible playbook for installation and periodic execution.
- All key steps are described in the README/operational documentation.

#### KPIs/Success Metrics for Phase 3
- Pipeline success rate ≥ 90% on main over 30 days.
- Average pipeline time ≤ 10 minutes.
- Critical findings from bandit/secrets scan = 0.
- Deployment time to a new host via Ansible ≤ 15 minutes.

`think about how and when to implement`
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
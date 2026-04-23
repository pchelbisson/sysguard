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

- **`Focus:`** turn SysGuard into a predictable policy-driven checker with machine-readable output and safe secret handling.

#### 2.1 Security Baseline (read-only first)
- **✅ Must have**
  - [x] SSH hardening checks (`PermitRootLogin`, `PasswordAuthentication`, custom `Port`).
  - [x] File permission checks (`/etc/shadow`, `/etc/passwd`, `/root`).
  - [x] Root execution warning (warning-only, not auto-fail).
- **🟡 Should have**
  - [x] Firewall status (UFW / firewalld or equivalent fallback).
  - [x] fail2ban status.
  - [x] Autostart/persistence hygiene (systemd + cron, read-only).
  - [x] SELinux / AppArmor status (read-only).
- **🔵 Could have**
  - [x] Simple secrets detection (regex, read-only scan scope only).

#### 2.2 JSON Reporting & Severity Policy
- **✅ Must have**
  - [x] Unified JSON report schema (single contract for every check result).
  - [x] `stdout` for JSON only; logs must go to file/stderr.
- **🟡 Should have**
  - [x] Severity model: `ok` / `warning` / `critical`.
  - [x] Stable exit-code policy mapped to severity (`0/1/2` or documented equivalent).
  - [x] CLI output controls for operator UX (`--output`, `--quiet`) without breaking JSON contract.

#### 2.3 Configuration & Secrets Hygiene
- **✅ Must have**
  - [x] Read sensitive values from environment variables only.
  - [x] Keep secrets out of `config.json`.
  - [x] Enforce deny-list keys: `password`, `token`, `secret`, `api_key`.
  - [ ] Implement masking helper and apply it in logs/report payloads.
- **🟡 Should have**
  - [ ] Validation for required env vars with clear startup error messages.

#### 2.4 Data Persistence (optional but high value)
- **🟡 Should have**
  - [ ] SQLite execution history:
    - [ ] `runs` table
    - [ ] `check_results` table
    - [ ] basic trend queries (disk usage, failures count)
- **🔵 Could have**
  - [ ] CLI analytics:
    - [ ] `sysguard history --last 20`
    - [ ] `sysguard trend --check disk_root --days 7`
  - [ ] Retention policy (`--retention-days`).

#### 2.5 Alerting
- **🟡 Should have**
  - [ ] Telegram / Webhook notifications on `critical` findings.

#### 2.6 Test & Quality Gates for Phase 2
- **✅ Must have**
  - [ ] Contract tests: every check returns the same schema.
  - [ ] Config tests and edge cases:
    - [ ] broken JSON
    - [ ] empty lists
    - [ ] invalid thresholds/types
  - [ ] Smoke e2e: minimal `main.py check` on test config in CI.
- **Operational rule**
  - [x] Read-only checks only (no mutating system state in Phase 2).
- **🔵 Could have**
  - [ ] Add pre-commit hook (`detect-secrets` or `gitleaks`) for local development.

#### 2.7 Practical next-iteration priorities (team sync)
- **Priority 1 — Quality gates first**
  - [ ] Add config edge-case tests (`broken JSON`, empty lists, invalid types/thresholds) to CI.
  - [ ] Add smoke e2e run (`main.py check` with minimal test config) as required CI job.
- **Priority 2 — Policy consistency**
  - [x] Finalize severity model (`ok` / `warning` / `critical`) and align check outputs.
  - [x] Finalize stable exit-code mapping and document contract (`0/1/2` or equivalent).
- **Priority 3 — Secrets hygiene hardening**
  - [ ] Read sensitive values from environment variables only.
  - [ ] Implement masking helper for logs/report payloads.
  - [ ] Keep secrets out of static config and enforce deny-list keys.
- **Codebase simplification (keep behavior unchanged)**
  - [ ] Extract CLI output/render concerns from `main.py` into a dedicated module for clearer ownership and testing.
  - [ ] Introduce structured logging pipeline (`structlog`) with centralized secret redaction processor.

#### Phase 2 Definition of Done (DoD)
- [ ] JSON output is stable and schema-validated in CI.
- [ ] Secrets are masked and not stored in config/report/logs in plain text.
- [ ] Security baseline checks are implemented and covered by tests.
- [ ] At least one smoke run is executed automatically in CI pipeline.a

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

### 🟤 Phase 3.5: Adoption & Product Readiness
- **`Why here:`** prepare distribution, onboarding, and market-facing packaging **after** core engineering reliability is in place.

#### 3.5.1 Packaging & Editions
- **✅ Must have**
  - [ ] Packaging options: `pipx` install, single-binary build, minimal Docker image.
  - [ ] Clear edition boundaries in docs: Community / Pro / Enterprise scope.

#### 3.5.2 Integration MVP & Pilot Experience
- **✅ Must have**
  - [ ] Integration MVP: webhook + Slack/Telegram notifications.
  - [ ] Customer-facing quickstart for 30-minute pilot on 3–10 hosts.
- **🟡 Should have**
  - [ ] CI/CD templates (GitHub Actions, GitLab CI) as reusable onboarding assets.

#### 3.5.3 Policy, Evidence, and ROI Packaging
- **🟡 Should have**
  - [ ] Policy packs (starter): Ubuntu baseline, Docker host baseline, SSH hardening.
  - [ ] Evidence exports: JSON + HTML/PDF audit summary for managers.
  - [ ] Basic ROI metrics in report (`critical_count`, MTTR proxy, trend delta).

#### 3.5.4 Commercial Extensions (infrastructure-safe track)
- **✅ Must have**
  - [ ] CI Pipeline Time Optimizer (phase-1 MVP): analyze CI jobs, detect bottlenecks, provide cache/split/parallelism recommendations.
- **🟡 Should have**
  - [ ] Log Cleanup & Cost Saver module (ClickHouse/ELK/Loki): expensive log-source detection + retention optimization + storage savings estimation.
  - [ ] Uptime + Incident Postmortem Assistant (no PII by design): endpoint checks, incident timeline capture, postmortem draft with action items.
- **🔵 Could have**
  - [ ] Billing telemetry hooks for paid feature gating (host count, policy packs, optimizer modules).
  - [ ] MSP mode (multi-client isolation + workspace model).
  - [ ] Public benchmark page with anonymized baseline stats (marketing growth loop).

#### 3.5.5 AI Explainability Add-on (optional, user-controlled API key)
- **🟡 Should have**
  - [ ] Integrate OpenAI/Anthropic API (opt-in): for each finding return short “why risky + 1-minute fix” guidance.
  - [ ] Data minimization mode: send only normalized config snippets (never full files / no secrets / no PII).
  - [ ] Provider abstraction + fallback templates when API is unavailable.
- **Risk controls**
  - [ ] Explicit consent toggle (`--ai-explain`), off by default.
  - [ ] Redaction pipeline before outbound requests.
  - [ ] Cost guardrails (token budget per run, per-host limits).

#### Phase 3.5 is considered complete when:
- [ ] A new user can install and run pilot checks in ≤ 30 minutes using quickstart docs.
- [ ] At least one notification path (webhook or Slack/Telegram) is validated in CI smoke tests.
- [ ] Community/Pro/Enterprise boundaries are documented and reflected in CLI help/docs.
- [ ] At least one commercial extension MVP (CI optimizer) is delivering measurable value.
- [ ] AI explanation feature is opt-in, redacted, and budget-limited by default.

### 🔴 Phase 4: Infrastructure as Code & Cloud
- **`Focus:`** Scaling and cloud-native services (Yandex Cloud).
- **`Terraform (IaC):`** Provision Virtual Machines and networks in the cloud using declarative code.
- **`Cloud Monitoring:`** Bridge SysGuard metrics with cloud-native monitoring services.

### 🟣 Phase 5: Orchestration & Observability
- **`Focus:`** Enterprise-grade high availability and visualization.
- **`K8s Deployment:`** Launch SysGuard as a CronJob or DaemonSet within a Kubernetes cluster.
- **`Helm Packaging:`** Create a Helm Chart for one-click installation in K8s.
- **`Observability Stack:`** Export data to Prometheus and visualize system health on a Grafana dashboard.
import os
import re
import logging
import stat
import subprocess
import shutil
from pathlib import Path
logger = logging.getLogger("sysguard")

SECURITY_FILE_RULES = [
    {
        "path": "/etc/shadow",
        "expected_mode": ["0640", "0600"],
        "expected_owner": 0,
        "expected_group": 42,  # TODO: implement a check named 'shadow' via grp
        "critical": True
    },
    {
        "path": "/etc/passwd",
        "expected_mode": ["0644"],
        "expected_owner": 0,
        "expected_group": 0,
        "critical": True
    }
]

# Global module constants
SSH_STANDARD_PATHS = [
    '/etc/ssh/sshd_config',
    '/usr/local/etc/ssh/sshd_config',
    './sshd_config'
]

SSH_DEFAULTS = {
    "PermitRootLogin": "prohibit-password",
    "PasswordAuthentication": "yes",
    "Port": "22"
}

STATUS_PRIORITY = {"OK": 0, "INFO": 0, "WARNING": 1, "ERROR": 2}

SYSTEMD_UNIT_DIRS = [
    "/etc/systemd/system",
    "/usr/lib/systemd/system",
    "/lib/systemd/system"
]

SYSTEMD_UNIT_SUFFIXES = (
    ".service",
    ".socket",
    ".timer",
    ".target",
    ".path",
    ".mount",
    ".automount",
    ".swap",
    ".slice"
)

CRON_PATH_GLOB = "/etc/cron*"
APPARMOR_PROFILES_PATH = "/sys/kernel/security/apparmor/profiles"
SELINUX_ENFORCE_PATH = "/sys/fs/selinux/enforce"
SELINUX_CONFIG_PATH = "/etc/selinux/config"

MAX_SECRET_FILE_SIZE_BYTES = 1024 * 1024  # 1 MB read limit per file

SECRET_PATTERNS = {
    "aws_access_key_id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,48}\b"),
    "private_key_header": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "generic_secret_assignment": re.compile(
        r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
}



def _check_ufw():
    """
    Checks the UFW status given the current access rights.
    """
    if not shutil.which("ufw"):
        return {"available": False, "active": False, "error": "Not installed"}
    
    # Forming a team
    cmd = ["ufw", "status"]
    
    # If we are not root, we try sudo in non-interactive mode
    if os.geteuid() != 0:
        # -n (non-interactive) prevents password waiting
        cmd = ["sudo", "-n"] + cmd
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=2 
        )
        
        if result.returncode != 0:
            # Most likely, sudo asked for a password or access was denied.
            return {"available": True, "active": False, "error": "Permission denied (sudo required)"}
            
        output = result.stdout.strip()
        return {
            "available": True, 
            "active": "Status: active" in output, 
            "output": output
        }
        
    except subprocess.TimeoutExpired:
        return {"available": True, "active": False, "error": "Check timed out"}
    except Exception as e:
        return {"available": True, "active": False, "error": str(e)}
    

def _check_iptables():
    """
    Checks iptables status, INPUT policy and rules presence.
    """
    if not shutil.which("iptables"):
        return {
            "available": False, 
            "input_policy": None, 
            "has_custom_rules": False
        }
    
    # Form a command taking into account the rights (use -n for sudo)
    cmd = ["iptables", "-L", "INPUT", "-n"]
    if os.geteuid() != 0:
        cmd = ["sudo", "-n"] + cmd
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=2
        )
        
        if result.returncode != 0:
            return {
                "available": True, 
                "input_policy": None, 
                "has_custom_rules": False,
                "error": "Permission denied (sudo -n failed)"
            }
        
        output = result.stdout.strip()
        if not output:
            return {"available": True, "input_policy": None, "has_custom_rules": False}

        # 1. Extract the Default Policy (ACCEPT/DROP/REJECT)
        # Search for the pattern: Chain INPUT (policy ACCEPT)
        policy_match = re.search(r"Chain INPUT \(policy (\w+)\)", output)
        input_policy = policy_match.group(1) if policy_match else None
        
        # 2. Check for the presence of rules
        # The output usually looks like this:
        # Line 1: Chain INPUT (policy ACCEPT)
        # Line 2: target prot opt ​​source destination
        # Line 3+: ... the rules themselves ...
        lines = [line for line in output.split("\n") if line.strip()]
        has_custom_rules = len(lines) > 2
        
        return {
            "available": True,
            "input_policy": input_policy,
            "has_custom_rules": has_custom_rules,
            "output": output
        }
        
    except subprocess.TimeoutExpired:
        return {"available": True, "input_policy": None, "has_custom_rules": False, "error": "Timeout"}
    except Exception as e:
        return {"available": True, "input_policy": None, "has_custom_rules": False, "error": str(e)}


def check_ssh_config(config_path_from_json=None):
    res_status = "OK"
    messages = []
    
    def update_status(new_status):
        nonlocal res_status
        if STATUS_PRIORITY[new_status] > STATUS_PRIORITY[res_status]:
            res_status = new_status

    # 1. Search for config (Priorities 1 and 2)
    target_path = config_path_from_json or next((p for p in SSH_STANDARD_PATHS if os.path.exists(p)), None)
    
    if not target_path:
        return {
            "check_name": "check_ssh_config",
            "status": "ERROR",
            "message": "sshd_config not found",
            "details": {}
        }

    # 2. Parsing
    found_settings = {}
    try:
        with open(target_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    key, val = parts[0].lower(), parts[1].lower()
                    # We compare with the keys from the defaults (but preserve the original key register)
                    for target_key in SSH_DEFAULTS:
                        if key == target_key.lower():
                            found_settings[target_key] = val
    except Exception as e:
        return {"check_name": "check_ssh_config", "status": res_status, "message": str(e), "details": {}}

    # Merger: Found Overlaps Defaults
    final_cfg = {**SSH_DEFAULTS, **found_settings}

    # 3. Logic checks
    # PermitRootLogin
    if final_cfg["PermitRootLogin"] == "yes":
        update_status("ERROR")
        messages.append("Root login allowed (yes)")
    elif final_cfg["PermitRootLogin"] not in ["no", "prohibit-password"]:
        update_status("WARNING")
        messages.append(f"Atypical meaning PermitRootLogin: {final_cfg['PermitRootLogin']}")

    # PasswordAuthentication
    if final_cfg["PasswordAuthentication"] == "yes":
        update_status("WARNING")
        messages.append("Password authentication is enabled")

    # Port (INFO - does not change status)
    if final_cfg["Port"] == "22":
        # Just a note, don't call update_status
        pass 

    return {
        "check_name": "check_ssh_config",
        "status": res_status,
        "message": ". ".join(messages) if messages else "SSH security settings are fine",
        "details": final_cfg
    }


def check_file_permissions(custom_rules=None):
    res_status = "OK"
    messages = []
    details = {}

    # Helper function for status escalation
    def update_status(new_status):
        nonlocal res_status
        if STATUS_PRIORITY.get(new_status, 0) > STATUS_PRIORITY.get(res_status, 0):
            res_status = new_status

    all_rules = SECURITY_FILE_RULES + (custom_rules or [])

    for rule in all_rules:
        path = rule["path"]
        is_critical = rule.get("critical", False)

        if not os.path.exists(path):
            if is_critical:
                update_status("ERROR")
                logger.error(f"Critical file missing: {path}")
                messages.append(f"Missing: {path}")
            else:
                # For non-critical files, simply INFO in the log and OK in the status
                logger.info(f"Optional file missing: {path}")
            details[path] = "MISSING"
            continue

        try:
            st = os.stat(path)
            # Format: 4 characters, octal, with leading zeros
            actual_mode = f"{st.st_mode & 0o777:04o}"
            actual_uid = st.st_uid
            actual_gid = st.st_gid

            # Let's normalize the expected modes (so that both "600" and "0600" work)
            expected_modes = [m.replace('0o', '').zfill(4) for m in rule["expected_mode"]]

            # 1. Checking rights
            if actual_mode not in expected_modes:
                update_status("ERROR" if is_critical else "WARNING")
                msg = f"{path}: insecure mode {actual_mode} (expected {expected_modes})"
                logger.warning(msg)
                messages.append(msg)

            # 2. Owner check (UID 0 is always root)
            if actual_uid != rule["expected_owner"]:
                update_status("ERROR") # The owner of a system file is not root - this is always an ERROR
                msg = f"{path}: wrong owner UID {actual_uid}"
                logger.error(msg)
                messages.append(msg)

            # 3. Check the group (if specified)
            if rule.get("expected_group") is not None:
                if actual_gid != rule["expected_group"]:
                    update_status("WARNING")
                    messages.append(f"{path}: wrong group GID {actual_gid}")

            details[path] = {"mode": actual_mode, "uid": actual_uid, "gid": actual_gid}

        except Exception as e:
            update_status("ERROR")
            logger.exception(f"Permission check failed for {path}")
            messages.append(f"Error {path}: {str(e)}")

    return {
        "check_name": "check_file_permissions",
        "status": res_status,
        "message": " | ".join(messages) if messages else "Permissions are correct",
        "details": details
    }

def check_firewall():
    """
    The main firewall check: UFW -> iptables cascade.
    """
    result = {
        "check_name": "check_firewall",
        "status": "UNKNOWN",
        "message": "",
        "details": {
            "backend": None,
            "active": False,
            "default_incoming": None,
            "has_rules": False,
            "recommendation": ""
        }
    }
    
    # 1. Checking UFW (highest priority)
    ufw = _check_ufw()
    
    if ufw.get("available") and ufw.get("active"):
        result["status"] = "OK"
        result["message"] = "UFW firewall is active"
        result["details"].update({
            "backend": "ufw",
            "active": True
        })
        return result

    # 2. UFW is inactive or unavailable - check iptables
    iptables = _check_iptables()
    
    # If iptables returns a permissions error (for example, sudo -n didn't work)
    if iptables.get("error") == "Permission denied":
        result["status"] = "WARNING"
        result["message"] = "Insufficient permissions to check firewall (run with sudo)"
        return result

    if not iptables.get("available"):
        result["status"] = "ERROR"
        result["message"] = "No firewall tools (UFW/iptables) found in system"
        return result

    # 3. Analyzing the state of iptables
    result["details"]["backend"] = "iptables"
    result["details"]["default_incoming"] = iptables["input_policy"]
    result["details"]["has_rules"] = iptables["has_custom_rules"]
    
    policy = iptables["input_policy"]
    has_rules = iptables["has_custom_rules"]

    if policy == "DROP":
        result["status"] = "OK"
        result["message"] = "iptables protection active (Policy: DROP)"
        result["details"]["active"] = True
    elif policy == "ACCEPT":
        if has_rules:
            # There are rules, but a permissive policy is suspicious (WARNING)
            result["status"] = "WARNING"
            result["message"] = "iptables policy is ACCEPT, but some rules exist"
            result["details"]["active"] = True
            result["details"]["recommendation"] = "Consider changing default policy to DROP"
        else:
            # There are no rules and the policy allows everything - this is a hole (ERROR/WARNING)
            result["status"] = "WARNING"
            result["message"] = "No active firewall protection detected (Policy: ACCEPT)"
            result["details"]["active"] = False
            result["details"]["recommendation"] = "Enable UFW or set iptables INPUT policy to DROP"
    else:
        result["status"] = "UNKNOWN"
        result["message"] = f"Unexpected iptables policy: {policy}"

    return result

def check_fail2ban():
    """
    Checks fail2ban availability and running status.
    """
    result = {
        "check_name": "check_fail2ban",
        "status": "UNKNOWN",
        "message": "",
        "details": {
            "available": False,
            "active": False,
            "backend": "fail2ban-client",
            "raw_status": ""
        }
    }

    if not shutil.which("fail2ban-client"):
        result["status"] = "WARNING"
        result["message"] = "fail2ban is not installed"
        return result

    cmd = ["fail2ban-client", "status"]
    if os.geteuid() != 0:
        cmd = ["sudo", "-n"] + cmd

    try:
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
    except subprocess.TimeoutExpired:
        result["status"] = "WARNING"
        result["message"] = "fail2ban status check timed out"
        result["details"]["available"] = True
        return result
    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = f"fail2ban check failed: {str(e)}"
        result["details"]["available"] = True
        return result

    output = (process.stdout or process.stderr or "").strip()
    result["details"]["available"] = True
    result["details"]["raw_status"] = output

    if process.returncode != 0:
        if "sorry, try again" in output.lower() or "permission denied" in output.lower():
            result["status"] = "WARNING"
            result["message"] = "Insufficient permissions to check fail2ban (run with sudo)"
        else:
            result["status"] = "WARNING"
            result["message"] = "fail2ban is installed but not running"
        return result

    if "Number of jail:" in output:
        result["status"] = "OK"
        result["message"] = "fail2ban is active"
        result["details"]["active"] = True
    else:
        result["status"] = "WARNING"
        result["message"] = "fail2ban returned unexpected status output"

    return result


def check_autostart_permissions():
    """Detect world-writable systemd/cron files that may allow persistence abuse."""
    result = {
        "check_name": "check_autostart_permissions",
        "status": "OK",
        "message": "No suspicious world-writable autostart files found",
        "details": {
            "systemd_world_writable": [],
            "cron_world_writable": []
        }
    }

    systemd_hits = []
    cron_hits = []

    for unit_dir in SYSTEMD_UNIT_DIRS:
        if not os.path.isdir(unit_dir):
            continue

        for root, _, files in os.walk(unit_dir):
            for file_name in files:
                if not file_name.endswith(SYSTEMD_UNIT_SUFFIXES):
                    continue

                file_path = os.path.join(root, file_name)
                try:
                    if os.stat(file_path).st_mode & stat.S_IWOTH:
                        systemd_hits.append(file_path)
                except OSError:
                    continue

    for cron_path in Path("/etc").glob("cron*"):
        try:
            cron_stat = os.stat(cron_path)
        except OSError:
            continue

        if cron_stat.st_mode & stat.S_IWOTH:
            cron_hits.append(str(cron_path))

        if os.path.isdir(cron_path):
            for root, _, files in os.walk(cron_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        if os.stat(file_path).st_mode & stat.S_IWOTH:
                            cron_hits.append(file_path)
                    except OSError:
                        continue

    result["details"]["systemd_world_writable"] = sorted(systemd_hits)
    result["details"]["cron_world_writable"] = sorted(cron_hits)

    if systemd_hits or cron_hits:
        result["status"] = "WARNING"
        result["message"] = (
            "World-writable autostart entries detected in systemd/cron paths"
        )

    return result

def check_mandatory_access_control():
    """
    Read-only check for host MAC controls (SELinux / AppArmor).
    """
    result = {
        "check_name": "check_mandatory_access_control",
        "status": "WARNING",
        "message": "SELinux/AppArmor status could not be detected",
        "details": {
            "selinux": {"available": False, "enabled": False, "mode": "unknown"},
            "apparmor": {"available": False, "enabled": False, "mode": "unknown"},
            "recommendation": "Enable SELinux or AppArmor for stronger host hardening"
        }
    }

    selinux_available = os.path.exists(SELINUX_ENFORCE_PATH) or os.path.exists(SELINUX_CONFIG_PATH)
    if selinux_available:
        result["details"]["selinux"]["available"] = True
        try:
            if os.path.exists(SELINUX_ENFORCE_PATH):
                with open(SELINUX_ENFORCE_PATH, "r", encoding="utf-8") as f:
                    enforce_value = f.read().strip()
                if enforce_value == "1":
                    result["details"]["selinux"]["enabled"] = True
                    result["details"]["selinux"]["mode"] = "enforcing"
                elif enforce_value == "0":
                    result["details"]["selinux"]["enabled"] = True
                    result["details"]["selinux"]["mode"] = "permissive"
            elif os.path.exists(SELINUX_CONFIG_PATH):
                with open(SELINUX_CONFIG_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        raw_line = line.strip().lower()
                        if not raw_line or raw_line.startswith("#"):
                            continue
                        if raw_line.startswith("selinux="):
                            mode = raw_line.split("=", 1)[1].strip()
                            result["details"]["selinux"]["mode"] = mode
                            if mode in ("enforcing", "permissive"):
                                result["details"]["selinux"]["enabled"] = True
                            break
        except OSError as e:
            result["details"]["selinux"]["mode"] = f"error: {str(e)}"

    apparmor_available = os.path.exists(APPARMOR_PROFILES_PATH) or shutil.which("aa-status")
    if apparmor_available:
        result["details"]["apparmor"]["available"] = True
        try:
            if os.path.exists(APPARMOR_PROFILES_PATH):
                with open(APPARMOR_PROFILES_PATH, "r", encoding="utf-8") as f:
                    profiles = [line for line in f.read().splitlines() if line.strip()]
                if profiles:
                    result["details"]["apparmor"]["enabled"] = True
                    result["details"]["apparmor"]["mode"] = "enforced_profiles_loaded"
                else:
                    result["details"]["apparmor"]["mode"] = "kernel_interface_present_no_profiles"
            elif shutil.which("aa-status"):
                cmd = ["aa-status", "--enabled"]
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if process.returncode == 0:
                    result["details"]["apparmor"]["enabled"] = True
                    result["details"]["apparmor"]["mode"] = "enabled"
                else:
                    result["details"]["apparmor"]["mode"] = "disabled_or_unknown"
        except (subprocess.SubprocessError, OSError) as e:
            result["details"]["apparmor"]["mode"] = f"error: {str(e)}"

    selinux_mode = result["details"]["selinux"]["mode"]
    apparmor_mode = result["details"]["apparmor"]["mode"]
    selinux_enabled = result["details"]["selinux"]["enabled"]
    apparmor_enabled = result["details"]["apparmor"]["enabled"]

    if selinux_mode == "enforcing" or apparmor_enabled:
        result["status"] = "OK"
        result["message"] = (
            f"MAC active: SELinux={selinux_mode}, AppArmor={apparmor_mode}"
        )
    elif selinux_enabled or result["details"]["apparmor"]["available"]:
        result["status"] = "WARNING"
        result["message"] = (
            f"MAC partially active: SELinux={selinux_mode}, AppArmor={apparmor_mode}"
        )
    else:
        result["status"] = "WARNING"
        result["message"] = "Neither SELinux nor AppArmor appears to be active"

    return result

def check_simple_secrets_scan(scan_scope=None):
    """
    Read-only regex scan for potentially hardcoded secrets in a limited scope.
    """
    result = {
        "check_name": "check_simple_secrets_scan",
        "status": "OK",
        "message": "No potential secrets detected in configured scan scope",
        "details": {
            "scanned_paths": [],
            "scanned_files": 0,
            "findings": [],
            "skipped_paths": []
        }
    }

    if not scan_scope:
        result["status"] = "WARNING"
        result["message"] = "Secrets scan scope is empty; configure secrets_scan_paths"
        return result

    candidate_files = []
    skipped_paths = []

    for raw_path in scan_scope:
        path = Path(raw_path).expanduser()

        if not path.exists():
            skipped_paths.append(f"{raw_path}: not found")
            continue

        if path.is_file():
            candidate_files.append(path)
            continue

        if path.is_dir():
            for root, _, files in os.walk(path):
                for file_name in files:
                    candidate_files.append(Path(root) / file_name)
            continue

        skipped_paths.append(f"{raw_path}: unsupported path type")

    findings = []
    scanned_files = 0
    scanned_paths = []

    for file_path in candidate_files:
        try:
            if file_path.stat().st_size > MAX_SECRET_FILE_SIZE_BYTES:
                skipped_paths.append(f"{file_path}: too large")
                continue
        except OSError as e:
            skipped_paths.append(f"{file_path}: unreadable ({str(e)})")
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                scanned_files += 1
                scanned_paths.append(str(file_path))
                for line_number, line in enumerate(f, start=1):
                    for pattern_name, pattern in SECRET_PATTERNS.items():
                        if pattern.search(line):
                            findings.append({
                                "path": str(file_path),
                                "line": line_number,
                                "pattern": pattern_name
                            })
        except OSError as e:
            skipped_paths.append(f"{file_path}: unreadable ({str(e)})")

    result["details"]["scanned_files"] = scanned_files
    result["details"]["scanned_paths"] = sorted(set(scanned_paths))
    result["details"]["skipped_paths"] = skipped_paths
    result["details"]["findings"] = findings

    if findings:
        result["status"] = "WARNING"
        result["message"] = (
            f"Potential secrets found: {len(findings)} hit(s) in {len(set(f['path'] for f in findings))} file(s)"
        )
    elif scanned_files == 0:
        result["status"] = "WARNING"
        result["message"] = "Secrets scan did not process any files in the configured scope"

    return result
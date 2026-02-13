import os
import logging
import stat
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

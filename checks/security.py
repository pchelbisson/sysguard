import os

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
            "message": "sshd_config не найден",
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

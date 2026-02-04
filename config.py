import logging
import json
import os

def load_config(config_path):
    """Separate config loading logic."""
    default_config = {
        "directories": [{"path": "/var/log", "critical": False}],
        "mounts": [{"path": "/", "critical": True}],
        "disk_paths": ["/"],
        "disk_threshold": 90,
        "check_hosts": ["127.0.0.1"],
        "required_ports": [],
        "lvm_threshold_gb": 1.0
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_data = json.load(f)
                if isinstance(file_data, dict):
                    default_config.update(file_data)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
    else:
        logging.warning(f"Config file not found: {config_path}, using defaults")
    return default_config
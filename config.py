import logging
import json
import os

SENSITIVE_ENV_SUFFIX = "_env"
SENSITIVE_CONFIG_DENYLIST = {"password", "token", "secret", "api_key"}

class ConfigValidationError(ValueError):
    """Raised when configuration is syntactically valid but violates policy."""


def _collect_plaintext_secret_paths(config, path="root"):
    """Collect paths of plaintext sensitive keys found in config."""
    found = []
    if isinstance(config, dict):
        for key, value in config.items():
            current_path = f"{path}.{key}"
            if (
                isinstance(key, str)
                and not key.endswith(SENSITIVE_ENV_SUFFIX)
                and key.lower() in SENSITIVE_CONFIG_DENYLIST
            ):
                found.append(current_path)
            found.extend(_collect_plaintext_secret_paths(value, current_path))
    elif isinstance(config, list):
        for index, item in enumerate(config):
            found.extend(_collect_plaintext_secret_paths(item, f"{path}[{index}]"))
    return found


def _validate_no_plaintext_secrets(config):
    """Reject config containing plaintext sensitive keys and report all matches."""
    found_paths = _collect_plaintext_secret_paths(config)
    if not found_paths:
        return

    raise ConfigValidationError(
        "Plaintext sensitive keys are not allowed in config.json: "
        + ", ".join(found_paths)
        + f". Use '*{SENSITIVE_ENV_SUFFIX}' keys with environment variable names."
    )


def _inject_sensitive_values_from_env(config, path="root"):
    """
    Load sensitive values only from environment variables.

    Convention:
    - Any config key ending with `_env` is treated as an environment variable name.
    - The actual value is injected under the same key name without `_env`.
    - Missing env vars are logged as errors and the target key is not injected.
    """
    
    if isinstance(config, list):
        return [_inject_sensitive_values_from_env(item, f"{path}[{idx}]") for idx, item in enumerate(config)]
    if not isinstance(config, dict):
        return config

    result = {}
    errors = []
    for key, value in config.items():
        current_path = f"{path}.{key}"
        prepared_value = _inject_sensitive_values_from_env(value, current_path)
        result[key] = prepared_value
        
        if not key.endswith(SENSITIVE_ENV_SUFFIX):
            continue

        if not isinstance(value, str) or not value.strip():
            errors.append(f"{current_path}: expected non-empty env var name string")
            continue

        env_var_name = value.strip()
        env_value = os.getenv(env_var_name)
        target_key = key[: -len(SENSITIVE_ENV_SUFFIX)]

        if env_value is None:
            errors.append(
                f"{current_path}: required environment variable '{env_var_name}' is not set"
            )
            continue

        result[target_key] = env_value
        
    if errors:
        raise ConfigValidationError(
            "Configuration requires environment variables that are missing/invalid:\n- "
            + "\n- ".join(errors)
        )

    return result

def load_config(config_path):
    """Separate config loading logic."""
    default_config = {
        "directories": [{"path": "/var/log", "critical": False}],
        "mounts": [{"path": "/", "critical": True}],
        "disk_paths": ["/"],
        "disk_threshold": 90,
        "check_hosts": ["127.0.0.1"],
        "required_ports": [],
        "lvm_threshold_gb": 1.0,
        "secrets_scan_paths": [],
        "history_db_path": "data/sysguard_history.db"
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_data = json.load(f)
                if isinstance(file_data, dict):
                    _validate_no_plaintext_secrets(file_data)
                    default_config.update(file_data)
        except ConfigValidationError:
            raise
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
    else:
        logging.warning(f"Config file not found: {config_path}, using defaults")
    return _inject_sensitive_values_from_env(default_config)
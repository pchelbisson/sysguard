import logging
import sys
from checks import check_disk, check_root, check_python_version, check_network, check_directory, check_mount, check_systemd, check_lvm
from checks.security import (
    check_ssh_config,
    check_file_permissions,
    check_firewall,
    check_fail2ban,
    check_autostart_permissions,
    check_mandatory_access_control,
    check_simple_secrets_scan
)

from report_schema import normalize_check_result


def _run_and_normalize(check_fn, *args, **kwargs):
    """Execute check function and normalize output into unified schema."""
    return normalize_check_result(check_fn(*args, **kwargs))

def run_health_checks(config):
    """Centralized launch of all checks."""
    report = []
    
    # Directory and mount checks (with sys.exit logic)
    for check_type in ["directories", "mounts"]:
        items = config.get(check_type, [])
        for item in items:
            path = item.get("path")
            crit = item.get("critical", False)
            
            res = _run_and_normalize(check_directory, path, crit) if check_type == "directories" else _run_and_normalize(check_mount, path, crit)
            report.append(res)
            
            if res.get("data", {}).get("is_critical_failure"):
                sys.exit(1)

    # Simple checks (drives, system, python)
    for path in config.get("disk_paths", ["/"]):
        report.append(_run_and_normalize(check_disk, path, threshold=config.get("disk_threshold")))
    
    report.append(_run_and_normalize(check_python_version))
    report.append(_run_and_normalize(check_root))
    report.append(_run_and_normalize(check_systemd))
    report.append(_run_and_normalize(check_lvm, threshold_gb=config.get("lvm_threshold_gb")))
    
    ssh_path = config.get("ssh_config_path")  # None или "" → auto-detect
    clean_path = ssh_path if ssh_path else None
    result = _run_and_normalize(check_ssh_config, clean_path)
    report.append(_run_and_normalize(check_file_permissions))
    report.append(_run_and_normalize(check_firewall))
    report.append(_run_and_normalize(check_fail2ban))
    report.append(_run_and_normalize(check_autostart_permissions))
    report.append(_run_and_normalize(check_mandatory_access_control))
    report.append(_run_and_normalize(check_simple_secrets_scan, config.get("secrets_scan_paths", [])))
    report.append(result)

    # Network check
    target_host = config.get("check_hosts", ["127.0.0.1"])[0]
    for port in config.get("required_ports", []):
        report.append(_run_and_normalize(check_network, target_host, port))
        
    return report

def print_summary(full_report):
    """Prints a report and returns False if there is an ERROR."""
    errors = sum(1 for r in full_report if r["status"] == "ERROR")
    warnings = sum(1 for r in full_report if r["status"] == "WARNING")

    logging.info("\n--- SUMMARY REPORT ---")
    for r in full_report:
        level = logging.INFO
        if r["status"] == "WARNING": level = logging.WARNING
        if r["status"] == "ERROR": level = logging.ERROR
        
        logging.log(level, f"{r['check_name']}: {r['message']}")

    if errors > 0:
        logging.critical(f"\n--- FAILED: {errors} errors found! ---")
        return False
    
    if warnings > 0:
        logging.warning(f"\n--- ATTENTION: {warnings} warnings found ---")
    else:
        logging.info("\n--- All checks passed ---")
        
    return True 
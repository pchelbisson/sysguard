import argparse
import sys
import subprocess
from pathlib import Path
import shutil
import os
import logging
import json
import socket
from logging_setup import setup_logging 

def handle_error(report_dict, msg, is_critical):
    """Updates the report dictionary and logs the error."""
    
    if is_critical:
        report_dict["status"] = "ERROR"
        report_dict["data"]["is_critical_failure"] = True
    else:
        report_dict["status"] = "WARNING"
    report_dict["message"] = msg

def check_lvm(threshold_gb=1.0):
    check_lvm_dict = {
        "check_name": "check_lvm",
        "status": "UNKNOWN",
        "message": "",
        "data": {
            "vg_name": None,
            "free_gb": None
        }
    }

    # Checking the availability of the utility
    if not shutil.which("vgs"):
        check_lvm_dict.update({"status": "WARNING", "message": "LVM tools not installed"})
        return check_lvm_dict

    # Permissions check (UID 0)
    if os.getuid() != 0:
        check_lvm_dict.update({"status": "WARNING", "message": "Root privileges required"})
        return check_lvm_dict

    try:
        # Call VGS directly
        result = subprocess.run(
            ["vgs", "--noheadings", "-o", "vg_name,vg_free", "--units", "g"],
            capture_output=True, text=True, check=True
        )
        output = result.stdout.strip()
        if not output:
            check_lvm_dict.update({"status": "OK", "message": "No volume groups found"})
            return check_lvm_dict
        
        # Parsing the first VG found
        # TODo: Phase 2 — handle multiple VGs
        parts = output.split()
        vg_name = parts[0]
        free_space = float(parts[1].replace('g', '').replace(',', '.'))
        
        check_lvm_dict["data"].update({
            "vg_name": vg_name,
            "free_gb": free_space
        })
        
        # Comparison with the threshold
        if free_space < threshold_gb:
            msg = f"Low free space in VG '{vg_name}': {free_space}GB (threshold: {threshold_gb}GB)"
            check_lvm_dict.update({"status": "WARNING", "message": msg})
        else:
            check_lvm_dict.update({"status": "OK", "message": "Free space is sufficient"})
            
    except Exception as e:
        # Any error is in WARNING
        error_msg = f"LVM check execution failed: {e}"
        check_lvm_dict.update({"status": "WARNING", "message": error_msg})

    return check_lvm_dict



def check_network(host, port):
    """Checking the availability of local ports."""
    check_network_dict = {
        "check_name": "check_network",
        "status": "UNKNOWN",
        "message": "",
        "data": {
            "host": host,
            "port": port
        }
    }
        
    try: # Create a socket object (AF_INET - IPv4, SOCK_STREAM - TCP)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            res = s.connect_ex((host, port))
            
            if res == 0:
                check_network_dict["status"] = "OK"
                check_network_dict["message"] = f"Port {port} on {host} is OPEN"
            else:
                check_network_dict["status"] = "WARNING"
                check_network_dict["message"] = f"Port {port} on {host} is CLOSED (Code: {res})"
                
    except Exception as e:
        check_network_dict["status"] = "ERROR"
        check_network_dict["message"] = f"Connection error: {e}"

    return check_network_dict

            
       

def check_python_version():
    """Сheck the installed version of Python"""
    major = sys.version_info.major
    minor = sys.version_info.minor
    current_version = f"{major}.{minor}"
    
    py_version_dict = {
        "check_name": "check_python_version",
        "status": "OK",
        "message": f"Python {current_version} is supported",
        "data": {
            "version": current_version,
            "min_required": "3.8"
        }
    }

    if sys.version_info < (3, 8):
        py_version_dict["status"] = "ERROR"
        py_version_dict["message"] = f"Python {current_version} is too old (min 3.8 required)"
    
    return py_version_dict

        
    
    
    

def check_root():
    """Checking root privileges"""
    check_root_dict = {"check_name": "check_root", 
                       "status": "UNKNOWN", 
                       "message": "", 
                       "data": {"uid": None}}
    try:
        euid = os.geteuid()
        check_root_dict["data"]["uid"] = euid
        
        if euid == 0:
            check_root_dict["status"] = "OK"
            check_root_dict["message"] = "Running with root privileges"
            
        else:
            # We are not leaving the program, we are just warning you
            check_root_dict["status"] = "WARNING"
            check_root_dict["message"] = f"Running as non-root user (UID: {euid})"
            
    except AttributeError:
        check_root_dict["status"] = "ERROR"
        check_root_dict["message"] = "System does not support UID checks (Non-POSIX OS)"
    return check_root_dict

def check_disk(path="/", threshold=90):
    """Checking free disk space."""
    check_disk_dict = {
        "check_name": "check_disk",
        "status": "UNKNOWN",
        "message": "",
        "data": {
            "path": path,
            "used_gb": 0,
            "total_gb": 0,
            "percent": 0       
        }
    }
    try:
        total, used, _ = shutil.disk_usage(path)
        percent_used = (used / total) * 100
        
        total_gb = total // (2**30)
        used_gb = used // (2**30)
        
        check_disk_dict["data"].update({
            "used_gb": used_gb,
            "total_gb": total_gb,
            "percent": round(percent_used, 1)
        })
        if percent_used > threshold:            
            check_disk_dict["status"] = "WARNING"
            check_disk_dict["message"] = f"Disk usage on {path} is high: {percent_used:.1f}%"
        else: 
            check_disk_dict["status"] = "OK"
            check_disk_dict["message"] = f"Disk space on {path} is within limits"
            
    except Exception as e:       
        check_disk_dict["status"] = "ERROR"
        check_disk_dict["message"] = str(e)
    return check_disk_dict

def check_systemd():
    """Checking system status via systemctl with structured output."""
    report = {
        "check_name": "check_systemd",
        "status": "UNKNOWN",
        "message": "",
        "data": {
            "state": "unknown",
            "failed_units": [],
            "is_linux": True
        }
    }
    
    try:
        result = subprocess.run(
            ["systemctl", "is-system-running"],
            capture_output=True,
            text=True,
            check=False
        )
        
        state = result.stdout.strip()
        report["data"]["state"] = state

        if state == "running":
            report["status"] = "OK"
            report["message"] = "System is running normally"
        elif state == "degraded":
            report["status"] = "WARNING"
            failed_res = subprocess.run(
                ["systemctl", "list-units", "--state=failed", "--plain", "--no-legend"],
                capture_output=True, text=True
            )
            failed_units = []
            for line in failed_res.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if parts:
                        failed_units.append(parts[0])
            
            report["data"]["failed_units"] = failed_units
            
            if failed_units:
                report["message"] = f"Degraded: {', '.join(failed_units)} failed"
            else:
                report["message"] = "System state: degraded (no specific failed units found)"
            
        else:
            report["status"] = "CRITICAL"
            report["message"] = f"System state: {state}"

    except FileNotFoundError:
        report["status"] = "WARNING"
        report["message"] = "systemctl not found"
        report["data"]["is_linux"] = False
    
    return report

    
def check_mount(path_str, is_critical=False):
    """Checks if the specified path is a mount point."""
    path = Path(path_str)
    
    check_mount_dict = {
        "check_name": "check_mount",
        "status": "UNKNOWN",
        "message": "",
        "data": {
            "path": path_str,
            "is_mounted": False,
            "is_critical_failure": False       
        }
    }
        
    if not os.path.ismount(path_str):
        handle_error(check_mount_dict, f"{path}: is NOT a mount point", is_critical)
    else:
        check_mount_dict["status"] = "OK"
        check_mount_dict["message"] = f"{path}: is a mount point"
        check_mount_dict["data"]["is_mounted"] = True

    return check_mount_dict


def check_directory(path_str, is_critical=False):
    """Check single directory accessibility."""
    path = Path(path_str)
    check_directory_dict = {
        "check_name": "check_directory",
        "status": "UNKNOWN",
        "message": "",
        "data": {
            "path": path_str,
            "exists": False,
            "is_dir": False,
            "readable": False,
            "is_critical_failure": False       
        }
    }
        
    if not path.exists():
        handle_error(check_directory_dict, f"{path}: Does not exist", is_critical)
        
    elif not path.is_dir():
        handle_error(check_directory_dict, f"{path}: Not a directory", is_critical)
        
    elif not os.access(path, os.R_OK): # pathlib is not yet a perfect replacement for access
        handle_error(check_directory_dict, f"{path}: Permission denied", is_critical)
    else:
        check_directory_dict["status"] = "OK"
        check_directory_dict["message"] = f"{path}: Accessible"
        check_directory_dict["data"].update({
            "exists": True,
            "is_dir": True,
            "readable": True
        })
    return check_directory_dict

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

def run_health_checks(config):
    """Centralized launch of all checks."""
    report = []
    
    # Directory and mount checks (with sys.exit logic)
    for check_type in ["directories", "mounts"]:
        items = config.get(check_type, [])
        for item in items:
            path = item.get("path")
            crit = item.get("critical", False)
            
            res = check_directory(path, crit) if check_type == "directories" else check_mount(path, crit)
            report.append(res)
            
            if res.get("data", {}).get("is_critical_failure"):
                sys.exit(1)

    # Simple checks (drives, system, python)
    for path in config.get("disk_paths", ["/"]):
        report.append(check_disk(path, threshold=config.get("disk_threshold")))
    
    report.append(check_python_version())
    report.append(check_root())
    report.append(check_systemd())
    report.append(check_lvm(threshold_gb=config.get("lvm_threshold_gb")))

    # Network check
    target_host = config.get("check_hosts", ["127.0.0.1"])[0]
    for port in config.get("required_ports", []):
        report.append(check_network(target_host, port))
        
    return report

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description="DevOps Utility: system guard.")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("check", help="Health check")
    
    args = parser.parse_args()
    
    if args.command == "check":
        config = load_config(args.config)
        logging.info("--- Starting Health Check ---")
        
        full_report = run_health_checks(config)
        
        # Final report
        errors = sum(1 for r in full_report if r["status"] == "ERROR")
        warnings = sum(1 for r in full_report if r["status"] == "WARNING")

        logging.info("\n--- SUMMARY REPORT ---")
        for r in full_report:
            level = logging.WARNING if r["status"] == "WARNING" else logging.INFO
            if r["status"] == "ERROR":
                level = logging.ERROR
            logging.log(level, f"[{r['status']}] {r['check_name']}: {r['message']}")

        if errors > 0:
            logging.critical(f"\n--- FAILED: {errors} errors found! ---")
            sys.exit(1)
        elif warnings > 0:
            logging.warning(f"\n--- ATTENTION: {warnings} warnings found ---")
        else:
            logging.info("\n--- All checks passed ---")
    else:
        parser.print_help()


if __name__ == "__main__":
    
    main()

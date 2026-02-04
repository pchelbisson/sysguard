import os
import sys
import logging
import subprocess

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
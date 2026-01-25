import argparse
import sys
import subprocess
from pathlib import Path
import shutil
import os
import logging
import json
import socket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='sysguard.log') 

def handle_error(report_dict, msg, is_critical):
    """Updates the report dictionary and logs the error."""
    
    if is_critical:
        report_dict["status"] = "ERROR"
        report_dict["data"]["is_critical_failure"] = True
        logging.error(f"CRITICAL ERROR: {msg}")
    else:
        report_dict["status"] = "WARNING"
        logging.warning(f"NON-CRITICAL WARNING: {msg}")

    report_dict["message"] = msg

def check_lvm():
    try:
        result = subprocess.run(
            ["sudo", "vgs", "--noheadings", "-o", "vg_name,vg_free", "--units", "g"],
            capture_output=True, text=True, check=True
        )
        output = result.stdout.strip()
        if not output:
            logging.info("LVM: No volume groups found")
            return
        
        # Split a string by spaces
        parts = output.split()
        vg_name = parts[0]
        # Remove the 'g' and convert to float
        free_space = float(parts[1].replace('g', '').replace(',', '.'))
        
        logging.info(f"LVM VG '{vg_name}': {free_space}GB free")
        
        if free_space < 1.0:
            logging.warning(f"LVM: Low free space in VG {vg_name} ({free_space}GB)")
            
    except Exception as e:
        logging.error(f"LVM check failed: {e}")


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
                logging.info(check_network_dict["message"])
            else:
                check_network_dict["status"] = "WARNING"
                check_network_dict["message"] = f"Port {port} on {host} is CLOSED (Code: {res})"
                logging.warning(check_network_dict["message"])
                
    except Exception as e:
        check_network_dict["status"] = "ERROR"
        check_network_dict["message"] = f"Connection error: {e}"
        logging.error(f"Error checking {host}:{port} - {e}")

    return check_network_dict

            
       

def check_python_version():
    """Сheck the installed version of Python"""
    # We get major and minor versions (for example, 3 and 15)
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
    # Example condition: Works only on Python 3.8 and above
    if sys.version_info < (3, 8):
        py_version_dict["status"] = "ERROR"
        py_version_dict["message"] = f"Python {current_version} is too old (min 3.8 required)"
        logging.error(py_version_dict["message"])
    else:
        logging.info(py_version_dict["message"])
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
            logging.info(check_root_dict["message"])
            
        else:
            # We are not leaving the program, we are just warning you
            check_root_dict["status"] = "WARNING"
            check_root_dict["message"] = f"Running as non-root user (UID: {euid})"
            logging.warning(check_root_dict["message"])
            
    except AttributeError:
        check_root_dict["status"] = "ERROR"
        check_root_dict["message"] = "System does not support UID checks (Non-POSIX OS)"
        logging.error(check_root_dict["message"])
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
            logging.warning(f" Critical: Disk usage on {path} is over {threshold}!")
        else: 
            check_disk_dict["status"] = "OK"
            check_disk_dict["message"] = f"Disk space on {path} is within limits"
            logging.info(f"Disk {path}: {used // (2**30)}GB / {total // (2**30)}GB ({percent_used:.1f}% used)")
            
    except Exception as e:       
        check_disk_dict["status"] = "ERROR"
        check_disk_dict["message"] = str(e)
        logging.error(f"Disk check failed for {path}: {e}")
    return check_disk_dict


def check_systemd():
    """Checking system status via systemctl."""
    try:
        result = subprocess.run(
            ["systemctl", "is-system-running"],
            capture_output=True,
            text=True,
            check=False # We will process the return code ourselves.
        )
        state = result.stdout.strip()
        if state == "running":
            logging.info("systemd: running")
            return True
        else:
            logging.info(f" systemd state: {state} (Reason: {result.stderr.strip()})")
            return False
    except FileNotFoundError:
        logging.error("systemctl not found. Is this a Linux system?")
        return False
    
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
        logging.info(f"{path}: is a mount point")

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
        logging.info(f"{path}: Accessible")
    return check_directory_dict

def main():
    config = {
    "directories": ["/var/log", "/etc"],
    "disk_threshold": 90
    }
    
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_data = json.load(f)
                if isinstance(file_data, dict):
                    config.update(file_data)
                    logging.info("Configuration loaded from config.json")
        except Exception as e:
            logging.error(f"Failed to load config.json: {e}")
            
    target_host = config.get("check_hosts")[0] if config.get("check_hosts") else "127.0.0.1"


    target_ports = config.get("required_ports", [])

    parser = argparse.ArgumentParser(description="DevOps Utility: system guard.")
    subparsers = parser.add_subparsers(dest="command") 

    check_parser = subparsers.add_parser("check", help="Health check")

    args = parser.parse_args()

    if args.command == "check":
        full_report = []
        logging.info("--- Starting Health Check ---")
        
        directories_data = config.get("directories", [{"path": "/", "critical": True}])
        for dir_info in directories_data:
            # Safely extract the path and critical flag
            path_str = dir_info.get("path")
            is_critical = dir_info.get("critical", False)
            dir_report = check_directory(path_str, is_critical)
            full_report.append(dir_report)
            # If the critical check fails, we stop execution (interrupt the script)
            if dir_report["data"]["is_critical_failure"]:
                logging.critical("System status: RED")
                sys.exit(1) 
        mount_data = config.get("mounts", [{"path": "/", "critical": True}])
        for mount_info in mount_data:
            mount_str = mount_info.get("path")
            is_critical_mount = mount_info.get("critical", False)
            mount_report = check_mount(mount_str, is_critical_mount)
            full_report.append(mount_report)
            if mount_report["data"]["is_critical_failure"]:
                logging.critical("System status: RED")
                sys.exit(1) 
        
        
        for disk_path in config.get("disk_paths", ["/"]):
            disk_result = check_disk(disk_path, threshold=config.get("disk_threshold"))
            full_report.append(disk_result)
        # We are launching checks
        full_report.append(check_python_version())
        full_report.append(check_root())
        
        logging.info(f"--- Checking Network Ports on {target_host} ---")
        for port in target_ports:
            net_result = check_network(target_host, port)
            full_report.append(net_result)

        
        errors_count = 0
        warnings_count = 0       
        
        logging.info("\n--- SUMMARY REPORT ---")

        for report in full_report:
            status = report.get("status")
            name = report.get("check_name")
            msg = report.get("message")
            
            logging.info(f"[{status}] {name}: {msg}")
            
            if status == "ERROR":
                errors_count += 1
            elif status == "WARNING":
                warnings_count += 1
                
        if errors_count > 0:
            logging.critical(f"\n--- FAILED: {errors_count} errors found! ---")
            sys.exit(1)
        elif warnings_count > 0:
            logging.warning(f"\n--- ATTENTION: {warnings_count} warnings found, but checks passed ---")
        else:    
            logging.info("\n--- All checks finished successfully ---")
        
        #lvm_ok = check_lvm()
        #disk_ok = check_disk("/", threshold=config.get("disk_threshold"))
        #systemd_ok = check_systemd()
        #network_ok = check_network(target_ports, target_host)
        #logging.info(f"Python version check: {py_version['version']}")
        #logging.info(f"DEBUG: Root report data is {root_result}")
        
        #logging.info(f"\n--- Checking Paths: {args.paths} ---")
        #dirs_ok = check_directories(args.paths) #Checks existence and rights
        
        # Let's add a mount check for each path here.
        #mounts_ok = True
        # We check all paths that the user passed via --paths
        #for p in args.paths:
            #if not check_mount(p):
                # We don't consider this a critical error for exit,
                # but we note that not everything is smooth.
                #mounts_ok = False
        #logging.info(f"FINAL REPORT STRUCTURE: {full_report}")
        # Deciding which code to exit with at the end
        #if not all([disk_ok, dirs_ok, systemd_ok, network_ok, lvm_ok]):
            #logging.critical("\n CRITICAL: SOME CHECKS FAILED")
            #sys.exit(1)
        
        #if not mounts_ok:
            #logging.warning("\n ADVISORY: Some paths are not mount points (this is often okay)")
            
        #logging.info("--- All checks passed successfully ---")
    else:
        parser.print_help()

if __name__ == "__main__":
    
    main()

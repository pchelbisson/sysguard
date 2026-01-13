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


def check_network(ports, host):
    """Checking the availability of local ports."""
    all_ok = True
    logging.info("--- Checking Network Ports ---")
    
    if isinstance(host, list):
        host = host[0]
        
    for port in ports:
        try:
            # Create a socket object (AF_INET - IPv4, SOCK_STREAM - TCP)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
            
            # The connect_ex method returns 0 on success.
                result = s.connect_ex((host, port))
            
                if result == 0:
                    logging.info(f"Port {port}: OPEN")
                else:
                    logging.warning(f"Host {host} Port {port}: CLOSED (Code: {result})")
                    all_ok = False
        except Exception as e:
            logging.error(f"Error checking port {port} on {host}: {e}")
            all_ok = False
    return all_ok

def check_python_version():
    # We get major and minor versions (for example, 3 and 15)
    major = sys.version_info.major
    minor = sys.version_info.minor
    logging.info(f"Current version of Python: {major}.{minor}")
    
    # Example condition: Works only on Python 3.8 and above
    if sys.version_info < (3, 8):
        logging.error("Error: Python 3.8+ is required")
        sys.exit(1)

def check_root():
    try:
        euid = os.geteuid()
        if euid == 0:
            logging.info("Running with root privileges")
        else:
            # We are not leaving the program, we are just warning you
            logging.warning("Warning: Running as non-root user (UID: {}). Some checks may be limited.".format(euid))
    except AttributeError:
        logging.error("System does not support UID checks (Non-POSIX OS)")

def check_disk(path="/", threshold=90):
    """Checking free disk space."""
    try:
        total, used, free = shutil.disk_usage(path)
        percent_used = (used / total) * 100
        logging.info(f"Disk {path}: {used // (2**30)}GB / {total // (2**30)}GB ({percent_used:.1f}% used)")
        if percent_used > threshold:
            logging.warning(f" Critical: Disk usage on {path} is over {threshold}!")
            return False
        return True
    except Exception as e:
        logging.warning(f"Disk check failed: {e}")
        return False


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
    
def check_mount(path="/"): # If the path is not specified, we check the root
    if os.path.ismount(path):
        logging.info(f"Path {path} is a mount point")
        return True
    else:
        logging.info(f"Path {path} is NOT a mount point")
        return False


def check_directories(paths):
    """Checking directory list."""
    all_ok = True
    for path_str in paths:
        path = Path(path_str)
        
        if not path.exists():
            logging.error(f"{path}: Does not exist")
            all_ok = False
        elif not path.is_dir():
            logging.error(f"{path}: Not a directory")
            all_ok = False
        elif not os.access(path, os.R_OK): # pathlib is not yet a perfect replacement for access
            logging.error(f"{path}: Permission denied")
            all_ok = False
        else:
            logging.info(f"{path}: Accessible")
    return all_ok

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
            
    target_host = config.get("check_hosts")[0] if isinstance(config.get("check_hosts"), list) else config.get("check_hosts", "127.0.0.1")

    target_ports = config.get("required_ports", [])

    parser = argparse.ArgumentParser(description="DevOps Utility: system guard.")
    subparsers = parser.add_subparsers(dest="command") 

    check_parser = subparsers.add_parser("check", help="Health check")
    check_parser.add_argument(
        "--paths", 
        nargs='+', 
        default=config.get("directories"), # Default values
        help="Directories to check"
    )

    args = parser.parse_args()

    if args.command == "check":
        check_python_version()
        check_root()
        
        logging.info("--- Starting Health Check ---")
        
        # We are launching checks
        lvm_ok = check_lvm()
        disk_ok = check_disk("/", threshold=config.get("disk_threshold"))
        systemd_ok = check_systemd()
        network_ok = check_network(target_ports, target_host)
        
        logging.info(f"\n--- Checking Paths: {args.paths} ---")
        dirs_ok = check_directories(args.paths) #Checks existence and rights
        
        # Let's add a mount check for each path here.
        mounts_ok = True
        # We check all paths that the user passed via --paths
        for p in args.paths:
            if not check_mount(p):
                # We don't consider this a critical error for exit,
                # but we note that not everything is smooth.
                mounts_ok = False

        # Deciding which code to exit with at the end
        if not all([disk_ok, dirs_ok, systemd_ok, network_ok, lvm_ok]):
            logging.critical("\n CRITICAL: SOME CHECKS FAILED")
            sys.exit(1)
        
        if not mounts_ok:
            logging.warning("\n ADVISORY: Some paths are not mount points (this is often okay)")
            
        logging.info("--- All checks passed successfully ---")
    else:
        parser.print_help()

if __name__ == "__main__":
    
    main()

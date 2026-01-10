import argparse
import sys
import subprocess
from pathlib import Path
import shutil
import os
import logging
import json


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='sysguard.log') 

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
        disk_ok = check_disk("/", threshold=config.get("disk_threshold"))
        systemd_ok = check_systemd()
        
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
        if not all([disk_ok, dirs_ok, systemd_ok]):
            logging.critical("\n CRITICAL: SOME CHECKS FAILED")
            sys.exit(1)
        
        if not mounts_ok:
            logging.warning("\n ADVISORY: Some paths are not mount points (this is often okay)")
            
        logging.info("--- All checks passed successfully ---")
    else:
        parser.print_help()

if __name__ == "__main__":
    
    main()

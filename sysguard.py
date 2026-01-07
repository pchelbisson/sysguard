import argparse
import sys
import subprocess
from pathlib import Path
import shutil
import os
import sys

def check_python_version():
    # We get major and minor versions (for example, 3 and 15)
    major = sys.version_info.major
    minor = sys.version_info.minor
    print(f"Current version of Python: {major}.{minor}")
    
    # Example condition: Works only on Python 3.8 and above
    if sys.version_info < (3, 8):
        print("Error: Python 3.8+ is required")
        sys.exit(1)

def check_root():
    try:
        euid = os.geteuid()
        if euid == 0:
            print("Running with root privileges")
        else:
            # We are not leaving the program, we are just warning you
            print("Warning: Running as non-root user (UID: {}). Some checks may be limited.".format(euid))
    except AttributeError:
        print("System does not support UID checks (Non-POSIX OS)")

def check_disk(path="/"):
    """Checking free disk space."""
    try:
        total, used, free = shutil.disk_usage(path)
        percent_used = (used / total) * 100
        print(f"Disk {path}: {used // (2**30)}GB / {total // (2**30)}GB ({percent_used:.1f}% used)")
        if percent_used > 90:
            print(f" Critical: Disk usage on {path} is over 90%!")
            return False
        return True
    except Exception as e:
        print(f"Disk check failed: {e}")
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
            print("systemd: running")
            return True
        else:
            print(f" systemd state: {state} (Reason: {result.stderr.strip()})")
            return False
    except FileNotFoundError:
        print("systemctl not found. Is this a Linux system?")
        return False
    
def check_mount(path="/"): # If the path is not specified, we check the root
    if os.path.ismount(path):
        print(f"Path {path} is a mount point")
        return True
    else:
        print(f"Path {path} is NOT a mount point")
        return False


def check_directories(paths):
    """Checking directory list."""
    all_ok = True
    for path_str in paths:
        path = Path(path_str)
        
        if not path.exists():
            print(f"{path}: Does not exist")
            all_ok = False
        elif not path.is_dir():
            print(f"{path}: Not a directory")
            all_ok = False
        elif not os.access(path, os.R_OK): # pathlib is not yet a perfect replacement for access
            print(f"{path}: Permission denied")
            all_ok = False
        else:
            print(f"{path}: Accessible")
    return all_ok

def main():
    #Check Pyhton version
    check_python_version()
    check_root()
    #check_mount()

    parser = argparse.ArgumentParser(description="DevOps Utility: system guard.")
    subparsers = parser.add_subparsers(dest="command") 

    check_parser = subparsers.add_parser("check", help="Health check")
    check_parser.add_argument(
        "--paths", 
        nargs='+', 
        default=["/var/log", "/etc"], # Default values
        help="Directories to check"
    )

    args = parser.parse_args()

    if args.command == "check":
        print("--- Starting Health Check ---")
        
        # We are launching checks
        disk_ok = check_disk("/")
        systemd_ok = check_systemd()
        
        print(f"\n--- Checking Paths: {args.paths} ---")
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
            print("\n CRITICAL: SOME CHECKS FAILED")
            sys.exit(1)
        
        if not mounts_ok:
            print("\n⚠️  ADVISORY: Some paths are not mount points (this is often okay)")
            
        print("--- All checks passed successfully ---")
    else:
        parser.print_help()

if __name__ == "__main__":
    
    main()

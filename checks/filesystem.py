import shutil
import subprocess
import os
from pathlib import Path
from utils import handle_error


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
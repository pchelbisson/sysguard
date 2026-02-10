import pytest
import sys
import os
import socket
from pathlib import Path
from unittest.mock import patch, MagicMock
from checks.network import check_network
from checks.system import (
    check_python_version, 
    check_root, 
    check_systemd
)

from checks.filesystem import (
    check_directory, 
    check_mount, 
    check_disk,
    check_lvm
)


def test_python_version_is_dict():
    """Checking that the function actually returns a dictionary (basic concept)"""
    result = check_python_version()
    assert isinstance(result, dict)
    assert result["check_name"] == "check_python_version"

def test_python_status_value():
    """We check that the status is either OK or ERROR"""
    result = check_python_version()
    assert result["status"] in ["OK", "ERROR", "WARNING"]


def test_check_root_is_ok():
    """Testing the scenario: user - ROOT (UID 0)"""
    # We 'override' the os.geteuid function so that it always returns 0
    with patch("os.geteuid") as mock_geteuid:
        mock_geteuid.return_value = 0
        
        result = check_root()
        
        assert result["status"] == "OK"
        assert "root privileges" in result["message"]
        assert result["data"]["uid"] == 0

def test_check_root_is_warning():
    """Testing the scenario: regular user (UID 1000)"""
    # We simulate a regular user
    with patch("os.geteuid") as mock_geteuid:
        mock_geteuid.return_value = 1000
        
        result = check_root()
        
        assert result["status"] == "WARNING"
        assert "non-root user" in result["message"]
        assert result["data"]["uid"] == 1000


def test_check_directory_etc_ok():
    """We test the real existing /etc directory (usually always available)"""
    result = check_directory("/etc", is_critical=False)
    
    assert result["status"] == "OK"
    assert result["data"]["exists"] is True
    assert "/etc" in result["message"]

def test_check_directory_not_found():
    """Testing a non-existent path"""
    path = "/tmp/really_weird_path_12345"
    result = check_directory(path, is_critical=False)
    
    assert result["status"] == "WARNING"
    assert "Does not exist" in result["message"]
    
def test_check_mount_root_ok():
    result = check_mount("/")
    
    assert result["status"] == "OK"
    assert result["data"]["is_mounted"] is True
    assert "is a mount point" in result["message"]

def test_check_mount_not_a_mount():
    """We test a regular folder (for example, /etc) that is not a mount point"""
    # /etc is just a folder inside the root filesystem, not a separate mount
    result = check_mount("/etc", is_critical=False)
    
    # Here we expect a WARNING, since we passed is_critical=False
    assert result["status"] == "WARNING"
    assert result["data"]["is_mounted"] is False
    assert "is NOT a mount point" in result["message"]

def test_check_mount_critical_failure():
    """Testing for a critical mounting error"""
    result = check_mount("/tmp/non_existent_mount", is_critical=True)
    
    assert result["status"] == "ERROR"
    

@patch("subprocess.run")
def test_check_systemd_degraded(mock_run):
    """Simulating a degraded state and a failed nginx service"""
    
    # Configuring responses for two subprocess.run calls
    # 1st call: Check system status
    # 2nd Challenge: List of Fallen Units
    mock_run.side_effect = [
        MagicMock(stdout="degraded"),
        MagicMock(stdout="nginx.service loaded failed failed  nginx server")
    ]

    result = check_systemd()

    assert result["status"] == "WARNING"
    assert "degraded" in result["data"]["state"]
    assert "nginx.service" in result["data"]["failed_units"]
    assert "nginx.service failed" in result["message"]


def test_check_disk_real_path():
    """Checking the actual space on the root partition"""
    result = check_disk("/", threshold=99.9) # Ставим высокий порог, чтобы точно было OK
    
    assert result["status"] == "OK"
    assert result["data"]["total_gb"] > 0
    assert isinstance(result["data"]["percent"], float)
    assert "/" in result["message"]

@patch("shutil.disk_usage")
def test_check_disk_high_usage(mock_usage):
    """Let's simulate the situation: 95 GB out of 100 GB is occupied (95%)"""
    mock_usage.return_value = (100 * 10**9, 95 * 10**9, 5 * 10**9)

    result = check_disk("/", threshold=90)

    assert result["status"] == "WARNING"
    assert result["data"]["percent"] >= 95.0
    assert "high" in result["message"]
    

def test_check_lvm_no_vgs_installed():
    """Test: VGS utility is missing from the system"""
    with patch("shutil.which", return_value=None):
        result = check_lvm()
        assert result["status"] == "WARNING"
        assert "not installed" in result["message"]

def test_check_lvm_no_root():
    """Test: Run as non-root (UID 1000)"""
    with patch("shutil.which", return_value="/usr/sbin/vgs"), \
         patch("os.getuid", return_value=1000):
        
        result = check_lvm()
        assert result["status"] == "WARNING"
        assert "Root privileges required" in result["message"]

@patch("subprocess.run")
def test_check_lvm_success_parsing(mock_run):
    """Test: successful parsing of vgs output (5GB free with 1GB limit)"""
    with patch("shutil.which", return_value="/usr/sbin/vgs"), \
         patch("os.getuid", return_value=0):
        
        # Simulating the output of VGS: Name_VG 5.00g
        mock_run.return_value = MagicMock(
            stdout="  ubuntu-vg 5.00g", 
            returncode=0
        )

        result = check_lvm(threshold_gb=1.0)
        
        assert result["status"] == "OK"
        assert result["data"]["vg_name"] == "ubuntu-vg"
        assert result["data"]["free_gb"] == 5.0
        assert "sufficient" in result["message"]
        


@patch("socket.socket")
def test_check_network_port_open(mock_socket_class):
    """Testing the scenario: Port is OPEN (connect_ex returns 0)"""
    # Create a mock for a socket instance
    mock_socket_instance = MagicMock()
    # The context manager (with) should return our mock instance
    mock_socket_class.return_value.__enter__.return_value = mock_socket_instance
    
    # Simulate a successful connection (code 0)
    mock_socket_instance.connect_ex.return_value = 0

    result = check_network("127.0.0.1", 80)

    assert result["status"] == "OK"
    assert "OPEN" in result["message"]
    # We check that the correct host and port were called.
    mock_socket_instance.connect_ex.assert_called_with(("127.0.0.1", 80))

@patch("socket.socket")
def test_check_network_port_closed(mock_socket_class):
    """Testing the scenario: Port CLOSED (connect_ex returns an error, for example 111)"""
    mock_socket_instance = MagicMock()
    mock_socket_class.return_value.__enter__.return_value = mock_socket_instance
    
    # We simulate a closed port (for example, code 111 - Connection refused)
    mock_socket_instance.connect_ex.return_value = 111

    result = check_network("127.0.0.1", 9999)

    assert result["status"] == "WARNING"
    assert "CLOSED" in result["message"]
    assert "(Code: 111)" in result["message"]



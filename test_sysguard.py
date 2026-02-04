import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch
from sysguard import check_python_version
from sysguard import check_root
from sysguard import check_directory
from sysguard import check_mount


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
    
import os


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

import pytest
import sys
from unittest.mock import patch
from sysguard import check_python_version
from sysguard import check_root

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

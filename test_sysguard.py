import pytest
import sys
import os
import socket
import stat
import json
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
from unittest.mock import patch, mock_open
from checks.network import check_network
from checks.security import (
    check_ssh_config,
    check_file_permissions,
    check_firewall,
    check_fail2ban,
    check_autostart_permissions,
    check_mandatory_access_control,
    check_simple_secrets_scan
)
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

from runner import run_health_checks
from report_schema import normalize_check_result, get_exit_code_for_report, build_report_document
from main import emit_json_report
from config import load_config


def test_python_version_is_dict():
    """Checking that the function actually returns a dictionary (basic concept)"""
    result = check_python_version()
    assert isinstance(result, dict)
    assert result["check_name"] == "check_python_version"

def test_python_status_value():
    """We check that the status is either OK or ERROR"""
    result = check_python_version()
    assert result["status"] in ["OK", "ERROR", "WARNING"]


def test_check_root_is_warning_when_root():
    """Testing the scenario: launch from ROOT (UID 0) -> expect WARNING"""
    with patch("os.geteuid") as mock_geteuid:
        mock_geteuid.return_value = 0
        
        result = check_root()
        
        # Now root is a WARNING from a security point of view
        assert result["status"] == "WARNING"
        assert "ROOT privileges" in result["message"]
        assert result["details"]["uid"] == 0
        assert "recommendation" in result["details"]

def test_check_root_is_ok_when_non_root():
    """Testing the scenario: regular user (UID 1000) -> expect OK"""
    with patch("os.geteuid") as mock_geteuid:
        mock_geteuid.return_value = 1000
        
        result = check_root()
        
        # Standard user is safe OK
        assert result["status"] == "OK"
        assert "standard user" in result["message"]
        assert result["details"]["uid"] == 1000

def test_check_root_os_error():
    """Testing the scenario: The system does not support UID checking (AttributeError)"""
    with patch("os.geteuid", side_effect=AttributeError):
        result = check_root()
        
        assert result["status"] == "ERROR"
        assert "Non-POSIX environment" in result["message"]



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


def test_ssh_config_not_found():
    """Test: config file not found"""
    with patch("os.path.exists", return_value=False):
        result = check_ssh_config()
        assert result["status"] == "ERROR"
        assert "not found" in result["message"]

def test_ssh_config_root_allowed():
    """Test: DANGER — PermitRootLogin yes"""
    # Simulating the contents of the sshd_config file
    ssh_content = "PermitRootLogin yes\nPasswordAuthentication no"
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=ssh_content)):
        
        result = check_ssh_config("/fake/path")
        
        assert result["status"] == "ERROR"
        assert "Root login allowed" in result["message"]
        assert result["details"]["PermitRootLogin"] == "yes"

def test_ssh_config_good_defaults():
    """Test: Everything by default (safe)"""
    # Empty file (SSH_DEFAULTS will work)
    ssh_content = "# All settings are commented out"
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=ssh_content)):
        
        result = check_ssh_config("/fake/path")
        
        # By default we have prohibit-password, so the status is OK
        # But PasswordAuthentication is 'yes' by default, so there will be a WARNING
        assert result["status"] == "WARNING"
        assert "Password authentication is enabled" in result["message"]
        
def test_load_config_injects_sensitive_value_from_env(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "api_key_env": "SYSGUARD_API_KEY",
                "required_ports": [443]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SYSGUARD_API_KEY", "super-secret-value")

    loaded = load_config(str(config_file))

    assert loaded["api_key"] == "super-secret-value"
    assert loaded["api_key_env"] == "SYSGUARD_API_KEY"
    assert loaded["required_ports"] == [443]


def test_load_config_skips_missing_sensitive_env(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "token_env": "SYSGUARD_MISSING_TOKEN"
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("SYSGUARD_MISSING_TOKEN", raising=False)

    loaded = load_config(str(config_file))

    assert "token" not in loaded
    assert loaded["token_env"] == "SYSGUARD_MISSING_TOKEN"
    
def test_load_config_rejects_plaintext_sensitive_value(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "api_key": "plaintext-should-not-be-used",
                "api_key_env": "SYSGUARD_API_KEY",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SYSGUARD_API_KEY", "env-value")

    loaded = load_config(str(config_file))
    assert "api_key" not in loaded


def test_load_config_reports_all_plaintext_secret_keys(tmp_path, caplog):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "api_key": "x",
                "nested": {
                    "token": "y",
                    "items": [{"secret": "z"}],
                },
                "password": "p",
            }
        ),
        encoding="utf-8",
    )

    loaded = load_config(str(config_file))

    assert "api_key" not in loaded
    error_messages = [record.getMessage() for record in caplog.records if record.levelname == "ERROR"]
    assert any("root.api_key" in msg for msg in error_messages)
    assert any("root.nested.token" in msg for msg in error_messages)
    assert any("root.nested.items[0].secret" in msg for msg in error_messages)
    assert any("root.password" in msg for msg in error_messages)
        

def test_file_permissions_all_ok():
    """Test: All files are in place, permissions and owners are correct"""
    # Simulating that files exist
    with patch("os.path.exists", return_value=True):
        # Simulating the os.stat result
        mock_stat = MagicMock()
        # 0o644 for passwd, 0o640 for shadow (in octal)
        # st_mode returns both the file type and the permissions, so we simulate only some of the permissions
        mock_stat.st_mode = 0o100644 
        mock_stat.st_uid = 0
        mock_stat.st_gid = 0
        
        with patch("checks.security.SECURITY_FILE_RULES", []), \
             patch("os.stat", return_value=mock_stat):
            # To simplify the test, we will pass one custom rule so as not to depend on global ones.
            custom_rule = [{
                "path": "/etc/passwd",
                "expected_mode": ["0644"],
                "expected_owner": 0,
                "expected_group": 0,
                "critical": True
            }]
            result = check_file_permissions(custom_rules=custom_rule)
            
            assert result["status"] == "OK"
            assert "Permissions are correct" in result["message"]

def test_file_permissions_missing_critical():
    """Test: Critical File Missing (ERROR)"""
    with patch("os.path.exists", return_value=False):
        custom_rule = [{
            "path": "/etc/shadow",
            "critical": True,
            "expected_mode": ["0600"],
            "expected_owner": 0
        }]
        result = check_file_permissions(custom_rules=custom_rule)
        
        assert result["status"] == "ERROR"
        assert "Missing: /etc/shadow" in result["message"]

def test_file_permissions_wrong_mode():
    """Test: Incorrect permissions (e.g. 0666 instead of 0644)"""
    with patch("os.path.exists", return_value=True):
        mock_stat = MagicMock()
        mock_stat.st_mode = 0o100666  # Too open rights
        mock_stat.st_uid = 0
        mock_stat.st_gid = 0
        
        with patch("os.stat", return_value=mock_stat):
            custom_rule = [{
                "path": "/etc/passwd",
                "expected_mode": ["0644"],
                "expected_owner": 0,
                "critical": True
            }]
            result = check_file_permissions(custom_rules=custom_rule)
            
            assert result["status"] == "ERROR"
            assert "insecure mode 0666" in result["message"]
            

def test_firewall_ufw_active():
    """Scenario 1: UFW is enabled"""
    with patch("checks.security._check_ufw") as mock_ufw:
        mock_ufw.return_value = {"available": True, "active": True}
        
        # We don't care what's in iptables as long as UFW is active.
        result = check_firewall()
        
        assert result["status"] == "OK"
        assert "UFW" in result["message"]
        assert result["details"]["backend"] == "ufw"

def test_firewall_fallback_to_iptables_secure():
    """Scenario 2: UFW is disabled, but iptables is in DROP (safe)"""
    with patch("checks.security._check_ufw") as mock_ufw, \
         patch("checks.security._check_iptables") as mock_ipt:
        
        mock_ufw.return_value = {"available": True, "active": False}
        mock_ipt.return_value = {
            "available": True, 
            "input_policy": "DROP", 
            "has_custom_rules": False
        }
        
        result = check_firewall()
        
        assert result["status"] == "OK"
        assert "iptables" in result["message"]
        assert "DROP" in result["message"]

def test_firewall_unprotected():
    """Scenario 3: All Off (ACCEPT) - Waiting for WARNING"""
    with patch("checks.security._check_ufw") as mock_ufw, \
         patch("checks.security._check_iptables") as mock_ipt:
        
        mock_ufw.return_value = {"available": True, "active": False}
        mock_ipt.return_value = {
            "available": True, 
            "input_policy": "ACCEPT", 
            "has_custom_rules": False
        }
        
        result = check_firewall()
        
        assert result["status"] == "WARNING"
        assert "No active firewall" in result["message"]
        
        
def test_fail2ban_not_installed():
    with patch("shutil.which", return_value=None):
        result = check_fail2ban()

        assert result["status"] == "WARNING"
        assert "not installed" in result["message"]
        assert result["details"]["available"] is False


def test_fail2ban_active_ok():
    with patch("shutil.which", return_value="/usr/bin/fail2ban-client"), \
         patch("os.geteuid", return_value=0), \
         patch("subprocess.run") as mock_run:

        mock_run.return_value = MagicMock(returncode=0, stdout="Status\n|- Number of jail: 1")

        result = check_fail2ban()

        assert result["status"] == "OK"
        assert "active" in result["message"]
        assert result["details"]["active"] is True


def test_fail2ban_installed_but_not_running():
    with patch("shutil.which", return_value="/usr/bin/fail2ban-client"), \
         patch("os.geteuid", return_value=0), \
         patch("subprocess.run") as mock_run:

        mock_run.return_value = MagicMock(returncode=255, stdout="", stderr="Failed to access socket path")

        result = check_fail2ban()

        assert result["status"] == "WARNING"
        assert "not running" in result["message"]
        assert result["details"]["available"] is True


def test_autostart_permissions_clean():
    with patch("checks.security.os.path.isdir", return_value=False), \
         patch("checks.security.Path.glob", return_value=[]):
        result = check_autostart_permissions()

        assert result["status"] == "OK"
        assert result["details"]["systemd_world_writable"] == []
        assert result["details"]["cron_world_writable"] == []


def test_autostart_permissions_detects_world_writable_entries():
    def fake_stat(path):
        st = MagicMock()
        if "bad.service" in str(path) or "cron.bad" in str(path):
            st.st_mode = stat.S_IWOTH
        else:
            st.st_mode = 0
        return st

    with patch("checks.security.os.path.isdir", return_value=True), \
         patch("checks.security.os.walk") as mock_walk, \
         patch("checks.security.Path.glob", return_value=[Path("/etc/cron.d"), Path("/etc/cron.bad")]), \
         patch("checks.security.os.stat", side_effect=fake_stat):

        def fake_walk(path):
            path = str(path)
            if path == "/etc/systemd/system":
                return [("/etc/systemd/system", [], ["bad.service", "ok.service"])]
            if path == "/etc/cron.d":
                return [("/etc/cron.d", [], ["cron.bad", "cron.ok"])]
            return []

        mock_walk.side_effect = fake_walk

        result = check_autostart_permissions()

        assert result["status"] == "WARNING"
        assert "/etc/systemd/system/bad.service" in result["details"]["systemd_world_writable"]
        assert "/etc/cron.d/cron.bad" in result["details"]["cron_world_writable"]
        assert "/etc/cron.bad" in result["details"]["cron_world_writable"]
        
def test_mandatory_access_control_selinux_enforcing():
    def fake_exists(path):
        return path == "/sys/fs/selinux/enforce"

    with patch("checks.security.os.path.exists", side_effect=fake_exists), \
         patch("builtins.open", mock_open(read_data="1\n")), \
         patch("checks.security.shutil.which", return_value=None):
        result = check_mandatory_access_control()

        assert result["status"] == "OK"
        assert result["details"]["selinux"]["mode"] == "enforcing"
        assert result["details"]["selinux"]["enabled"] is True


def test_mandatory_access_control_none_active():
    with patch("checks.security.os.path.exists", return_value=False), \
         patch("checks.security.shutil.which", return_value=None):
        result = check_mandatory_access_control()

        assert result["status"] == "WARNING"
        assert "Neither SELinux nor AppArmor" in result["message"]
        
def test_simple_secrets_scan_detects_findings(tmp_path):
    scanned_dir = tmp_path / "scan"
    scanned_dir.mkdir()
    secret_file = scanned_dir / "app.env"
    secret_file.write_text("API_KEY=super-secret-key-123456\n", encoding="utf-8")

    result = check_simple_secrets_scan([str(scanned_dir)])

    assert result["status"] == "WARNING"
    assert result["details"]["scanned_files"] == 1
    assert len(result["details"]["findings"]) >= 1
    assert result["details"]["findings"][0]["pattern"] in {
        "generic_secret_assignment"
    }


def test_simple_secrets_scan_ok_when_clean(tmp_path):
    scanned_dir = tmp_path / "scan-clean"
    scanned_dir.mkdir()
    clean_file = scanned_dir / "notes.txt"
    clean_file.write_text("hello world\n", encoding="utf-8")

    result = check_simple_secrets_scan([str(scanned_dir)])

    assert result["status"] == "OK"
    assert result["details"]["scanned_files"] == 1
    assert result["details"]["findings"] == []


def test_simple_secrets_scan_empty_scope_warning():
    result = check_simple_secrets_scan([])

    assert result["status"] == "WARNING"
    assert "scope is empty" in result["message"]
    
def test_normalize_check_result_unifies_details_and_status():
    raw = {
        "check_name": "legacy_check",
        "status": "CRITICAL",
        "message": "legacy critical",
        "details": {"legacy": True},
    }

    normalized = normalize_check_result(raw)

    assert set(normalized.keys()) == {"check_name", "status", "severity", "message", "data"}
    assert normalized["status"] == "ERROR"
    assert normalized["severity"] == "critical"
    assert normalized["data"] == {"legacy": True}


def test_run_health_checks_returns_unified_schema_for_all_results():
    config = {
        "directories": [],
        "mounts": [],
        "disk_paths": ["/"],
        "disk_threshold": 95,
        "required_ports": [],
        "check_hosts": ["127.0.0.1"],
        "lvm_threshold_gb": 1.0,
        "secrets_scan_paths": [],
    }

    report = run_health_checks(config)

    assert isinstance(report, list)
    assert report
    for item in report:
        assert set(item.keys()) == {"check_name", "status", "severity", "message", "data"}
        assert isinstance(item["check_name"], str)
        assert item["status"] in {"OK", "WARNING", "ERROR"}
        assert item["severity"] in {"ok", "warning", "critical"}
        assert isinstance(item["message"], str)
        assert isinstance(item["data"], dict)
        
def test_exit_code_policy_is_mapped_to_max_severity():
    report = [
        {"check_name": "a", "status": "OK", "severity": "ok", "message": "", "data": {}},
        {"check_name": "b", "status": "WARNING", "severity": "warning", "message": "", "data": {}},
    ]
    assert get_exit_code_for_report(report) == 1

    report.append({"check_name": "c", "status": "ERROR", "severity": "critical", "message": "", "data": {}})
    assert get_exit_code_for_report(report) == 2
    
def test_build_report_document_contains_schema_version_and_summary():
    report = [
        {"check_name": "x", "status": "OK", "severity": "ok", "message": "ok", "data": {}},
    ]
    document = build_report_document(report)

    assert document["schema_version"] == "1.0"
    assert "generated_at" in document
    assert document["summary"]["severity"] == "ok"
    assert document["summary"]["exit_code"] == 0
    assert document["summary"]["checks_total"] == 1
    assert document["results"] == report
        
def test_emit_json_report_writes_stdout_when_default(monkeypatch):
    fake_stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    emit_json_report([{"check_name": "x", "status": "OK", "message": "ok", "data": {}}])

    parsed = json.loads(fake_stdout.getvalue())
    assert parsed["schema_version"] == "1.0"
    assert parsed["summary"]["severity"] == "ok"
    assert isinstance(parsed["results"], list)
    assert parsed["results"][0]["check_name"] == "x"


def test_emit_json_report_writes_file_and_suppresses_stdout(tmp_path, monkeypatch):
    fake_stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    output_path = tmp_path / "report.json"

    emit_json_report(
        [{"check_name": "x", "status": "OK", "message": "ok", "data": {}}],
        output_path=str(output_path),
    )

    assert fake_stdout.getvalue() == ""
    parsed = json.loads(output_path.read_text(encoding="utf-8"))
    assert parsed["schema_version"] == "1.0"
    assert parsed["results"][0]["status"] == "OK"


def test_emit_json_report_quiet_suppresses_stdout(monkeypatch):
    fake_stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    emit_json_report(
        [{"check_name": "x", "status": "OK", "message": "ok", "data": {}}],
        quiet=True,
    )

    assert fake_stdout.getvalue() == ""
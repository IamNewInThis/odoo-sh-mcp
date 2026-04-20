"""Tests for SSH tools using mocked subprocess."""

import subprocess
from unittest.mock import MagicMock, patch

from odoo_sh_mcp.tools.ssh import (
    ssh_exec,
    ssh_update_module,
    ssh_restart,
    ssh_read_log,
    ssh_upload_file,
)

HOST = "staging.odoo.com"
USER = "12345"
KEY = "~/.ssh/id_ed25519"


def make_proc(returncode=0, stdout="", stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


@patch("subprocess.run")
def test_ssh_exec_returns_output(mock_run):
    mock_run.return_value = make_proc(stdout="odoo\n")
    result = ssh_exec(HOST, USER, KEY, "whoami")
    assert result["exit_code"] == 0
    assert result["stdout"] == "odoo\n"


@patch("subprocess.run")
def test_ssh_exec_captures_stderr(mock_run):
    mock_run.return_value = make_proc(returncode=1, stderr="command not found\n")
    result = ssh_exec(HOST, USER, KEY, "badcmd")
    assert result["exit_code"] == 1
    assert "command not found" in result["stderr"]


@patch("subprocess.run")
def test_ssh_update_module_calls_odoo_update(mock_run):
    mock_run.return_value = make_proc(stdout="done\n")
    result = ssh_update_module(HOST, USER, KEY, "sale_custom")
    called_cmd = mock_run.call_args[0][0]
    assert "odoo-update sale_custom" in " ".join(called_cmd)
    assert result["exit_code"] == 0


@patch("subprocess.run")
def test_ssh_restart_calls_odoosh_restart(mock_run):
    mock_run.return_value = make_proc()
    ssh_restart(HOST, USER, KEY)
    called_cmd = mock_run.call_args[0][0]
    assert "odoosh-restart" in " ".join(called_cmd)


@patch("subprocess.run")
def test_ssh_read_log_uses_tail(mock_run):
    mock_run.return_value = make_proc(stdout="INFO log line\n")
    result = ssh_read_log(HOST, USER, KEY, lines=50)
    called_cmd = mock_run.call_args[0][0]
    assert "tail" in " ".join(called_cmd)
    assert "50" in " ".join(called_cmd)
    assert result["stdout"] == "INFO log line\n"


@patch("subprocess.run")
def test_ssh_upload_file_calls_scp(mock_run):
    mock_run.return_value = make_proc()
    result = ssh_upload_file(HOST, USER, KEY, "/tmp/my_file.py", "/home/odoo/src/user/mymod/my_file.py")
    calls = [" ".join(c[0][0]) for c in mock_run.call_args_list]
    assert any("scp" in c for c in calls)
    assert result["uploaded"] == "/home/odoo/src/user/mymod/my_file.py"


@patch("subprocess.run")
def test_ssh_upload_file_raises_on_scp_failure(mock_run):
    # mkdir succeeds, scp fails
    mock_run.side_effect = [
        make_proc(),
        make_proc(returncode=1, stderr="No such file"),
    ]
    try:
        ssh_upload_file(HOST, USER, KEY, "/tmp/bad.py", "/home/odoo/src/user/mod/bad.py")
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "scp failed" in str(e)

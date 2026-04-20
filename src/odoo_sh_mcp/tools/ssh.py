"""SSH/SFTP tools for direct Odoo.sh server access via system ssh/scp."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _ssh_args(host: str, user: str, key_path: str) -> list[str]:
    expanded = os.path.expanduser(key_path)
    return [
        "ssh",
        "-i", expanded,
        "-o", "StrictHostKeyChecking=accept-new",
        f"{user}@{host}",
    ]


def ssh_exec(host: str, user: str, key_path: str, command: str) -> dict:
    args = _ssh_args(host, user, key_path) + [command]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"SSH command timed out after 120s: {command}")
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def ssh_upload_file(
    host: str, user: str, key_path: str, local_path: str, remote_path: str
) -> dict:
    expanded_key = os.path.expanduser(key_path)
    remote_dir = str(Path(remote_path).parent)

    # Ensure remote directory exists
    ssh_exec(host, user, key_path, f"mkdir -p {remote_dir}")

    args = [
        "scp",
        "-i", expanded_key,
        "-o", "StrictHostKeyChecking=accept-new",
        local_path,
        f"{user}@{host}:{remote_path}",
    ]
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"scp failed: {result.stderr}")
    return {"uploaded": remote_path}


def ssh_update_module(host: str, user: str, key_path: str, module_name: str) -> dict:
    return ssh_exec(host, user, key_path, f"odoo-update {module_name}")


def ssh_restart(host: str, user: str, key_path: str) -> dict:
    return ssh_exec(host, user, key_path, "odoosh-restart")


def ssh_read_log(host: str, user: str, key_path: str, lines: int = 100) -> dict:
    return ssh_exec(host, user, key_path, f"tail -n {lines} ~/logs/odoo.log")

"""Tier 4 tools: Module management — list, install, upgrade via XML-RPC."""

from __future__ import annotations

from typing import Any

from ..client import OdooClient

_MODULE_STATES = {
    "installed": "Installed",
    "uninstalled": "Not installed",
    "to install": "Queued for install",
    "to upgrade": "Queued for upgrade",
    "to remove": "Queued for removal",
    "uninstallable": "Uninstallable",
}


def list_modules(
    client: OdooClient,
    state: str | None = None,
    keyword: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    List installed (or all) modules.

    Args:
        state:   Filter by state: 'installed', 'uninstalled', etc.
        keyword: Filter by name/summary keyword
        limit:   Max results (default 50)
    """
    domain: list[Any] = []
    if state:
        domain.append(("state", "=", state))
    if keyword:
        domain.append("|")
        domain.append(("name", "ilike", keyword))
        domain.append(("summary", "ilike", keyword))

    records = client.search_read(
        "ir.module.module",
        domain,
        ["name", "shortdesc", "state", "latest_version", "author"],
        limit=limit,
        order="name asc",
    )
    return [
        {
            "name": r["name"],
            "description": r.get("shortdesc") or "",
            "state": r.get("state"),
            "version": r.get("latest_version") or "",
            "author": r.get("author") or "",
        }
        for r in records
    ]


def _trigger_module_action(client: OdooClient, module_name: str, action: str) -> dict[str, Any]:
    """Internal helper to install or upgrade a module."""
    records = client.search_read(
        "ir.module.module",
        [("name", "=", module_name)],
        ["id", "name", "state"],
    )
    if not records:
        raise ValueError(f"Module '{module_name}' not found.")

    rec = records[0]
    module_id = rec["id"]
    current_state = rec["state"]

    if action == "install":
        if current_state == "installed":
            return {"module": module_name, "result": "already_installed", "state": current_state}
        client.execute("ir.module.module", "button_immediate_install", [[module_id]])
        return {"module": module_name, "result": "install_triggered", "previous_state": current_state}

    if action == "upgrade":
        if current_state != "installed":
            raise ValueError(f"Module '{module_name}' is not installed (state: {current_state}).")
        client.execute("ir.module.module", "button_immediate_upgrade", [[module_id]])
        return {"module": module_name, "result": "upgrade_triggered", "previous_state": current_state}

    raise ValueError(f"Unknown action: {action}")


def install_module(client: OdooClient, module_name: str) -> dict[str, Any]:
    """
    Install an Odoo module via XML-RPC.

    Args:
        module_name: Technical module name, e.g. 'sale_management'

    Note: This triggers the install on the running instance. On Odoo SH,
    prefer upgrading via git push; use this for quick testing only.
    """
    return _trigger_module_action(client, module_name, "install")


def upgrade_module(client: OdooClient, module_name: str) -> dict[str, Any]:
    """
    Upgrade an already-installed Odoo module via XML-RPC.

    Args:
        module_name: Technical module name, e.g. 'sale_management'
    """
    return _trigger_module_action(client, module_name, "upgrade")

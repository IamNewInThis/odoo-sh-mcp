"""Tier 2 tools: View introspection — XML arch, xmlid resolution, field location."""

from __future__ import annotations

import re
from typing import Any

from ..client import OdooClient

VIEW_TYPES = {"form", "tree", "list", "kanban", "search", "pivot", "graph", "calendar", "gantt", "activity"}


def get_views(client: OdooClient, model: str, view_type: str | None = None) -> list[dict[str, Any]]:
    """
    Return the XML arch of all views (or a specific type) for a model.

    Args:
        model:     Technical model name, e.g. 'sale.order'
        view_type: Optional filter: 'form', 'tree', 'kanban', 'search', etc.
    """
    domain: list[Any] = [("model", "=", model), ("type", "!=", "qweb")]
    if view_type:
        vt = view_type.strip().lower()
        # Odoo 17 renamed 'tree' → 'list' but keeps both
        domain.append(("type", "=", vt))

    records = client.search_read(
        "ir.ui.view",
        domain,
        ["name", "type", "arch_db", "xml_id", "priority", "active", "inherit_id"],
        order="model asc, type asc, priority asc",
    )

    results = []
    for r in records:
        results.append(
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "xml_id": r.get("xml_id") or "",
                "priority": r.get("priority", 16),
                "active": r.get("active", True),
                "inherit_id": r["inherit_id"][1] if r.get("inherit_id") else None,
                "arch": r.get("arch_db") or "",
            }
        )
    return results


def get_view_by_xmlid(client: OdooClient, xmlid: str) -> dict[str, Any]:
    """
    Resolve an xmlid (e.g. 'sale.view_order_form') and return its full arch.

    Args:
        xmlid: External ID in 'module.identifier' format
    """
    if "." not in xmlid:
        raise ValueError(f"xmlid must be 'module.identifier', got: '{xmlid}'")

    module, name = xmlid.split(".", 1)

    # Look up via ir.model.data
    data_recs = client.search_read(
        "ir.model.data",
        [("module", "=", module), ("name", "=", name), ("model", "=", "ir.ui.view")],
        ["res_id"],
    )
    if not data_recs:
        raise ValueError(f"xmlid '{xmlid}' not found in ir.model.data.")

    view_id = data_recs[0]["res_id"]
    view_recs = client.search_read(
        "ir.ui.view",
        [("id", "=", view_id)],
        ["name", "type", "model", "arch_db", "xml_id", "priority", "active", "inherit_id"],
    )
    if not view_recs:
        raise ValueError(f"ir.ui.view with id {view_id} not found.")

    r = view_recs[0]
    return {
        "id": r["id"],
        "xml_id": xmlid,
        "name": r["name"],
        "type": r["type"],
        "model": r["model"],
        "priority": r.get("priority", 16),
        "active": r.get("active", True),
        "inherit_id": r["inherit_id"][1] if r.get("inherit_id") else None,
        "arch": r.get("arch_db") or "",
    }


def find_field_in_view(client: OdooClient, model: str, field_name: str) -> list[dict[str, Any]]:
    """
    Find which views of a model contain a given field and where.

    Args:
        model:      Technical model name, e.g. 'sale.order'
        field_name: Field technical name, e.g. 'partner_id'
    """
    views = get_views(client, model)
    matches = []

    # Simple regex to find the field in arch XML
    pattern = re.compile(
        rf"""(?:name=['\"]{re.escape(field_name)}['\"]|field[^>]*?name=['\"]{re.escape(field_name)}['\"])""",
        re.IGNORECASE,
    )

    for view in views:
        arch = view.get("arch", "")
        if not arch:
            continue

        occurrences = []
        for i, line in enumerate(arch.splitlines(), start=1):
            if pattern.search(line):
                occurrences.append({"line": i, "content": line.strip()})

        if occurrences:
            matches.append(
                {
                    "view_id": view["id"],
                    "view_name": view["name"],
                    "view_type": view["type"],
                    "xml_id": view["xml_id"],
                    "occurrences": occurrences,
                }
            )

    return matches

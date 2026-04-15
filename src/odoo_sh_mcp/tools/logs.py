"""Tier 5 tools: Server log access via ir.logging model."""

from __future__ import annotations

from typing import Any

from ..client import OdooClient

LEVELS = {"debug", "info", "warning", "error", "critical"}


def get_server_logs(
    client: OdooClient,
    level: str = "error",
    limit: int = 50,
    module: str | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch recent server logs from ir.logging.

    Args:
        level:  Minimum log level to return: 'debug', 'info', 'warning', 'error', 'critical'
        limit:  Number of log entries (default 50, max 200)
        module: Optional filter by logger name / module, e.g. 'odoo.addons.sale'
    """
    level = level.lower()
    if level not in LEVELS:
        raise ValueError(f"Invalid level '{level}'. Must be one of: {', '.join(sorted(LEVELS))}")

    # Map levels to numeric priority for domain filter
    level_order = ["debug", "info", "warning", "error", "critical"]
    valid_levels = level_order[level_order.index(level):]

    domain: list[Any] = [("level", "in", [l.upper() for l in valid_levels])]
    if module:
        domain.append(("name", "ilike", module))

    limit = max(1, min(limit, 200))

    records = client.search_read(
        "ir.logging",
        domain,
        ["name", "level", "message", "func", "line", "path", "create_date"],
        limit=limit,
        order="id desc",
    )

    return [
        {
            "timestamp": r.get("create_date"),
            "level": r.get("level"),
            "logger": r.get("name"),
            "func": r.get("func"),
            "line": r.get("line"),
            "path": r.get("path"),
            "message": (r.get("message") or "")[:2000],  # cap long tracebacks
        }
        for r in records
    ]

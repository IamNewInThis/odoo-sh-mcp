"""Entry point for the odoo-sh-mcp MCP server."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import OdooClient
from .tools import orm, views, modules, logs
from .scaffold import generator

load_dotenv()

app = Server("odoo-sh-mcp")

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    # Tier 1 — ORM
    Tool(
        name="get_model_fields",
        description=(
            "Return all fields for an Odoo model with their type, label, required, "
            "readonly, relation and compute info. Use before writing any model code."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name, e.g. 'account.move'",
                }
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_model_info",
        description=(
            "Return ORM metadata for a model: description, installed modules, "
            "transient flag, and inherited models."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name, e.g. 'sale.order'",
                }
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="search_models",
        description=(
            "Search for Odoo models whose technical name or description contains a keyword. "
            "Useful for discovering available models."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Partial model name or description, e.g. 'account', 'sale'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 30)",
                    "default": 30,
                },
            },
            "required": ["keyword"],
        },
    ),
    Tool(
        name="search_records",
        description=(
            "Search and read records from any Odoo model. "
            "Use to query business data: orders, customers, invoices, products, etc."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name, e.g. 'sale.order', 'res.partner', 'account.move'",
                },
                "domain": {
                    "type": "array",
                    "description": "Odoo domain filter, e.g. [[\"name\", \"=\", \"S00482\"]]",
                    "default": [],
                },
                "fields": {
                    "type": "array",
                    "description": "Fields to return, e.g. [\"name\", \"partner_id\", \"amount_total\"]. Empty = all fields.",
                    "items": {"type": "string"},
                    "default": [],
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records (default 10)",
                    "default": 10,
                },
                "order": {
                    "type": "string",
                    "description": "Sort order, e.g. 'date_order desc'",
                },
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="create_record",
        description=(
            "Create a record in any Odoo model using ORM create(). "
            "Use carefully because this writes directly to the Odoo database."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name, e.g. 'res.partner', 'sale.order', 'account.move'",
                },
                "values": {
                    "type": "object",
                    "description": "Field values for create(), e.g. {\"name\": \"ACME\"}",
                    "additionalProperties": True,
                },
            },
            "required": ["model", "values"],
        },
    ),
    Tool(
        name="update_record",
        description=(
            "Update an existing record in any Odoo model using ORM write(). "
            "Use carefully because this writes directly to the Odoo database."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name, e.g. 'res.partner', 'sale.order'",
                },
                "record_id": {
                    "type": "integer",
                    "description": "Database ID of the record to update",
                },
                "values": {
                    "type": "object",
                    "description": "Field values to write, e.g. {\"name\": \"New Name\"}",
                    "additionalProperties": True,
                },
            },
            "required": ["model", "record_id", "values"],
        },
    ),
    Tool(
        name="delete_record",
        description=(
            "Delete a single record from any Odoo model using ORM unlink(). "
            "Use carefully because this permanently removes business data when Odoo allows it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name, e.g. 'res.partner', 'sale.order', 'account.move'",
                },
                "record_id": {
                    "type": "integer",
                    "description": "Database ID of the record to delete",
                },
            },
            "required": ["model", "record_id"],
        },
    ),
    # Tier 2 — Views
    Tool(
        name="get_views",
        description=(
            "Return the XML arch of all views (or a specific type) for a model. "
            "Essential before writing view inheritances."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name, e.g. 'sale.order'",
                },
                "view_type": {
                    "type": "string",
                    "description": "Optional: 'form', 'tree'/'list', 'kanban', 'search', etc.",
                },
            },
            "required": ["model"],
        },
    ),
    Tool(
        name="get_view_by_xmlid",
        description=(
            "Resolve an external ID (xmlid) and return the full XML arch of the view. "
            "Use to inspect a specific view before inheriting it."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "xmlid": {
                    "type": "string",
                    "description": "External ID in 'module.identifier' format, e.g. 'sale.view_order_form'",
                }
            },
            "required": ["xmlid"],
        },
    ),
    Tool(
        name="find_field_in_view",
        description=(
            "Find which views of a model contain a given field and show the exact lines. "
            "Use to locate where a field appears before adding siblings."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Technical model name",
                },
                "field_name": {
                    "type": "string",
                    "description": "Field technical name, e.g. 'partner_id'",
                },
            },
            "required": ["model", "field_name"],
        },
    ),
    # Tier 3 — Scaffold (local filesystem)
    Tool(
        name="scaffold_module",
        description=(
            "Create a minimal Odoo module skeleton on your local filesystem "
            "(__manifest__.py, __init__.py, models/, security/). Does NOT touch Odoo SH."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Module technical name, e.g. 'my_custom_module'",
                },
                "path": {
                    "type": "string",
                    "description": "Parent directory path where the module folder will be created",
                },
            },
            "required": ["name", "path"],
        },
    ),
    Tool(
        name="create_model_file",
        description=(
            "Generate a Python model file inside an existing local module. "
            "Does NOT touch Odoo SH."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "module_path": {
                    "type": "string",
                    "description": "Absolute path to the module root directory",
                },
                "model_name": {
                    "type": "string",
                    "description": "Odoo model name, e.g. 'sale.order.custom'",
                },
                "fields": {
                    "type": "array",
                    "description": "List of field definitions",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "string": {"type": "string"},
                            "required": {"type": "boolean"},
                            "readonly": {"type": "boolean"},
                            "comodel_name": {"type": "string"},
                            "help": {"type": "string"},
                        },
                        "required": ["name", "type"],
                    },
                },
            },
            "required": ["module_path", "model_name", "fields"],
        },
    ),
    Tool(
        name="create_view_inheritance",
        description=(
            "Generate an XML view inheritance file in a local module's views/ directory. "
            "Does NOT touch Odoo SH."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "module_path": {
                    "type": "string",
                    "description": "Absolute path to the module root directory",
                },
                "base_xmlid": {
                    "type": "string",
                    "description": "xmlid of the view to inherit, e.g. 'sale.view_order_form'",
                },
                "fields_to_add": {
                    "type": "array",
                    "description": "Fields to add to the view",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "widget": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                },
                "position": {
                    "type": "string",
                    "description": "XPath position: 'after', 'before', 'inside', 'replace'",
                    "default": "after",
                },
                "ref_field": {
                    "type": "string",
                    "description": "Field name to use as XPath anchor (defaults to first field in fields_to_add)",
                },
            },
            "required": ["module_path", "base_xmlid", "fields_to_add"],
        },
    ),
    # Tier 4 — Modules
    Tool(
        name="list_modules",
        description="List Odoo modules with their state (installed/uninstalled) and version.",
        inputSchema={
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Filter by state: 'installed', 'uninstalled', etc.",
                },
                "keyword": {
                    "type": "string",
                    "description": "Filter by name or summary keyword",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 50)",
                    "default": 50,
                },
            },
        },
    ),
    Tool(
        name="install_module",
        description=(
            "Install an Odoo module via XML-RPC. "
            "On Odoo SH prefer git push; use this for quick testing only."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Technical module name, e.g. 'sale_management'",
                }
            },
            "required": ["module_name"],
        },
    ),
    Tool(
        name="upgrade_module",
        description="Upgrade an already-installed Odoo module via XML-RPC.",
        inputSchema={
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Technical module name, e.g. 'sale_management'",
                }
            },
            "required": ["module_name"],
        },
    ),
    # Tier 5 — Logs
    Tool(
        name="get_server_logs",
        description=(
            "Fetch recent server logs from ir.logging. "
            "Useful for debugging errors after module install/upgrade."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "description": "Minimum level: 'debug', 'info', 'warning', 'error', 'critical'",
                    "default": "error",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of entries (default 50, max 200)",
                    "default": 50,
                },
                "module": {
                    "type": "string",
                    "description": "Optional logger name filter, e.g. 'odoo.addons.sale'",
                },
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# MCP handlers
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    client = OdooClient()

    try:
        result: Any = _dispatch(client, name, arguments)
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]
    except Exception as exc:
        return [TextContent(type="text", text=f"Unexpected error: {exc}")]

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


def _dispatch(client: OdooClient, name: str, args: dict[str, Any]) -> Any:
    # Tier 1
    if name == "get_model_fields":
        return orm.get_model_fields(client, args["model"])
    if name == "get_model_info":
        return orm.get_model_info(client, args["model"])
    if name == "search_models":
        return orm.search_models(client, args["keyword"], limit=args.get("limit", 30))
    if name == "search_records":
        return orm.search_records(
            client,
            args["model"],
            domain=args.get("domain", []),
            fields=args.get("fields", []),
            limit=args.get("limit", 10),
            order=args.get("order", ""),
        )
    if name == "create_record":
        return orm.create_record(client, args["model"], args["values"])
    if name == "update_record":
        return orm.update_record(client, args["model"], args["record_id"], args["values"])
    if name == "delete_record":
        return orm.delete_record(client, args["model"], args["record_id"])

    # Tier 2
    if name == "get_views":
        return views.get_views(client, args["model"], args.get("view_type"))
    if name == "get_view_by_xmlid":
        return views.get_view_by_xmlid(client, args["xmlid"])
    if name == "find_field_in_view":
        return views.find_field_in_view(client, args["model"], args["field_name"])

    # Tier 3 — scaffold (no Odoo client needed)
    if name == "scaffold_module":
        return generator.scaffold_module(args["name"], args["path"])
    if name == "create_model_file":
        return generator.create_model_file(
            args["module_path"], args["model_name"], args["fields"]
        )
    if name == "create_view_inheritance":
        return generator.create_view_inheritance(
            args["module_path"],
            args["base_xmlid"],
            args["fields_to_add"],
            position=args.get("position", "after"),
            ref_field=args.get("ref_field"),
        )

    # Tier 4
    if name == "list_modules":
        return modules.list_modules(
            client,
            state=args.get("state"),
            keyword=args.get("keyword"),
            limit=args.get("limit", 50),
        )
    if name == "install_module":
        return modules.install_module(client, args["module_name"])
    if name == "upgrade_module":
        return modules.upgrade_module(client, args["module_name"])

    # Tier 5
    if name == "get_server_logs":
        return logs.get_server_logs(
            client,
            level=args.get("level", "error"),
            limit=args.get("limit", 50),
            module=args.get("module"),
        )

    raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import asyncio

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()

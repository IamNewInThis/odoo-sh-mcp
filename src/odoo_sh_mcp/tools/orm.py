"""Tier 1 tools: ORM introspection — model fields, info, search."""

from __future__ import annotations

from typing import Any

from ..client import OdooClient


def get_model_fields(client: OdooClient, model: str) -> dict[str, Any]:
    """
    Return all fields for a model with type, label, required, readonly, relation.

    Args:
        model: Technical model name, e.g. 'account.move'
    """
    try:
        fields: dict[str, Any] = client.execute(
            model,
            "fields_get",
            [],
            {"attributes": ["string", "type", "required", "readonly", "relation", "help", "store", "compute"]},
        )
    except Exception as exc:
        raise ValueError(f"Model '{model}' not found or not accessible: {exc}") from exc

    result: dict[str, Any] = {}
    for fname, fmeta in sorted(fields.items()):
        entry: dict[str, Any] = {
            "type": fmeta.get("type"),
            "string": fmeta.get("string"),
            "required": fmeta.get("required", False),
            "readonly": fmeta.get("readonly", False),
            "store": fmeta.get("store", True),
        }
        if fmeta.get("relation"):
            entry["relation"] = fmeta["relation"]
        if fmeta.get("compute"):
            entry["compute"] = fmeta["compute"]
        if fmeta.get("help"):
            entry["help"] = fmeta["help"]
        result[fname] = entry

    return {"model": model, "field_count": len(result), "fields": result}


def get_model_info(client: OdooClient, model: str) -> dict[str, Any]:
    """
    Return ORM metadata for a model: _name, _description, _inherit, parent module.

    Args:
        model: Technical model name, e.g. 'sale.order'
    """
    records = client.search_read(
        "ir.model",
        [("model", "=", model)],
        ["name", "model", "info", "modules", "transient"],
    )
    if not records:
        raise ValueError(f"Model '{model}' not found in ir.model.")

    rec = records[0]

    # Fetch inherited models via ir.model.fields (Many2many _inherit isn't directly exposed)
    # Use fields_get with 'groups' to cross-reference; instead, pull from ir.model.inherit if available
    inherited: list[str] = []
    try:
        inherit_recs = client.search_read(
            "ir.model.inherit",
            [("model_id.model", "=", model)],
            ["parent_id"],
        )
        inherited = [r["parent_id"][1] if isinstance(r["parent_id"], list) else str(r["parent_id"]) for r in inherit_recs]
    except Exception:
        # ir.model.inherit may not exist in older Odoo versions
        pass

    return {
        "name": rec.get("name"),
        "model": rec.get("model"),
        "description": rec.get("info") or "",
        "modules": rec.get("modules") or "",
        "transient": rec.get("transient", False),
        "inherits": inherited,
    }


def search_records(
    client: OdooClient,
    model: str,
    domain: list[Any],
    fields: list[str],
    limit: int = 10,
    order: str = "",
) -> list[dict[str, Any]]:
    """
    Search and read records from any Odoo model.

    Args:
        model:  Technical model name, e.g. 'sale.order'
        domain: Odoo domain filter, e.g. [['name', '=', 'S00482']]
        fields: List of field names to return, e.g. ['name', 'partner_id', 'amount_total']
        limit:  Max records to return (default 10)
        order:  Sort order, e.g. 'date_order desc'
    """
    try:
        records = client.search_read(model, domain, fields, limit=limit, order=order)
    except Exception as exc:
        raise ValueError(f"Error querying '{model}': {exc}") from exc
    return records


def create_record(client: OdooClient, model: str, values: dict[str, Any]) -> dict[str, Any]:
    """
    Create a record in any Odoo model.

    Args:
        model:  Technical model name, e.g. 'res.partner'
        values: Field values for create(), e.g. {'name': 'ACME'}
    """
    if not values:
        raise ValueError("values cannot be empty.")

    try:
        record_id = client.execute(model, "create", [values])
    except Exception as exc:
        raise ValueError(f"Error creating record in '{model}': {exc}") from exc

    return {
        "model": model,
        "id": record_id,
        "created": True,
    }


def delete_record(client: OdooClient, model: str, record_id: int) -> dict[str, Any]:
    """
    Delete a single record from any Odoo model.

    Args:
        model:     Technical model name, e.g. 'res.partner'
        record_id: Database ID of the record to delete
    """
    if not isinstance(record_id, int) or record_id <= 0:
        raise ValueError("record_id must be a positive integer.")

    try:
        deleted = client.execute(model, "unlink", [[record_id]])
    except Exception as exc:
        raise ValueError(f"Error deleting record {record_id} from '{model}': {exc}") from exc

    return {
        "model": model,
        "id": record_id,
        "deleted": bool(deleted),
    }


def search_models(client: OdooClient, keyword: str, limit: int = 30) -> list[dict[str, Any]]:
    """
    Search for models whose technical name or description contains a keyword.

    Args:
        keyword: Partial model name or description, e.g. 'account', 'sale'
        limit:   Max results (default 30)
    """
    records = client.search_read(
        "ir.model",
        ["|", ("model", "ilike", keyword), ("name", "ilike", keyword)],
        ["name", "model", "modules"],
        limit=limit,
        order="model asc",
    )
    return [
        {
            "model": r["model"],
            "name": r["name"],
            "modules": r.get("modules") or "",
        }
        for r in records
    ]

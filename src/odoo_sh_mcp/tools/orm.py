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

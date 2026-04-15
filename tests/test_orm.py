"""Tests for ORM tools using a mock XML-RPC client."""

import pytest
from unittest.mock import MagicMock

from odoo_sh_mcp.tools.orm import get_model_fields, get_model_info, search_models


def make_client(execute_return=None, search_read_return=None):
    client = MagicMock()
    if execute_return is not None:
        client.execute.return_value = execute_return
    if search_read_return is not None:
        client.search_read.return_value = search_read_return
    return client


def test_get_model_fields_returns_fields():
    mock_fields = {
        "name": {"type": "char", "string": "Name", "required": True, "readonly": False},
        "partner_id": {"type": "many2one", "string": "Partner", "relation": "res.partner", "required": False, "readonly": False},
    }
    client = make_client(execute_return=mock_fields)
    result = get_model_fields(client, "sale.order")

    assert result["model"] == "sale.order"
    assert result["field_count"] == 2
    assert result["fields"]["name"]["type"] == "char"
    assert result["fields"]["partner_id"]["relation"] == "res.partner"


def test_get_model_fields_raises_on_error():
    client = MagicMock()
    client.execute.side_effect = Exception("Model not found")

    with pytest.raises(ValueError, match="not found"):
        get_model_fields(client, "nonexistent.model")


def test_search_models_returns_list():
    mock_records = [
        {"model": "account.move", "name": "Journal Entry", "modules": "account"},
        {"model": "account.move.line", "name": "Journal Item", "modules": "account"},
    ]
    client = make_client(search_read_return=mock_records)
    result = search_models(client, "account")

    assert len(result) == 2
    assert result[0]["model"] == "account.move"


def test_get_model_info_raises_if_not_found():
    client = make_client(search_read_return=[])

    with pytest.raises(ValueError, match="not found"):
        get_model_info(client, "unknown.model")

"""Tests for local scaffold tools (no Odoo connection required)."""

import pytest
import tempfile
from pathlib import Path

from odoo_sh_mcp.scaffold.generator import (
    scaffold_module,
    create_model_file,
    create_view_inheritance,
)


def test_scaffold_module_creates_structure():
    with tempfile.TemporaryDirectory() as tmp:
        result = scaffold_module("test_module", tmp)
        module_dir = Path(tmp) / "test_module"

        assert module_dir.exists()
        assert (module_dir / "__manifest__.py").exists()
        assert (module_dir / "__init__.py").exists()
        assert (module_dir / "models" / "__init__.py").exists()
        assert (module_dir / "security" / "ir.model.access.csv").exists()
        assert result["module"] == "test_module"


def test_scaffold_module_raises_if_exists():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold_module("dup_module", tmp)
        with pytest.raises(FileExistsError):
            scaffold_module("dup_module", tmp)


def test_create_model_file():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold_module("mymod", tmp)
        module_path = str(Path(tmp) / "mymod")

        result = create_model_file(
            module_path,
            "mymod.record",
            [
                {"name": "name", "type": "char", "string": "Name", "required": True},
                {"name": "partner_id", "type": "many2one", "string": "Partner", "comodel_name": "res.partner"},
            ],
        )

        target = Path(result["file"])
        assert target.exists()
        content = target.read_text()
        assert "class MymodRecord" in content
        assert "fields.Char" in content
        assert "fields.Many2one" in content
        assert "comodel_name='res.partner'" in content


def test_create_view_inheritance():
    with tempfile.TemporaryDirectory() as tmp:
        scaffold_module("mymod", tmp)
        module_path = str(Path(tmp) / "mymod")

        result = create_view_inheritance(
            module_path,
            "sale.view_order_form",
            [{"name": "x_custom_field"}, {"name": "x_another_field", "widget": "many2many_tags"}],
            position="after",
            ref_field="partner_id",
        )

        out_file = Path(result["file"])
        assert out_file.exists()
        content = out_file.read_text()
        assert 'ref="sale.view_order_form"' in content
        assert 'name="x_custom_field"' in content
        assert 'widget="many2many_tags"' in content
        assert 'position="after"' in content

"""Tier 3 tools: Local scaffold generator — creates Odoo module files on disk."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIELD_TYPE_MAP = {
    "char": "fields.Char",
    "text": "fields.Text",
    "integer": "fields.Integer",
    "float": "fields.Float",
    "boolean": "fields.Boolean",
    "date": "fields.Date",
    "datetime": "fields.Datetime",
    "many2one": "fields.Many2one",
    "one2many": "fields.One2many",
    "many2many": "fields.Many2many",
    "selection": "fields.Selection",
    "monetary": "fields.Monetary",
    "html": "fields.Html",
    "binary": "fields.Binary",
}


def _class_name(model_name: str) -> str:
    """'sale.order.line' → 'SaleOrderLine'"""
    return "".join(part.capitalize() for part in model_name.replace(".", "_").split("_"))


def _model_to_filename(model_name: str) -> str:
    """'sale.order.line' → 'sale_order_line'"""
    return model_name.replace(".", "_")


# ---------------------------------------------------------------------------
# scaffold_module
# ---------------------------------------------------------------------------

def scaffold_module(name: str, path: str) -> dict[str, Any]:
    """
    Create a minimal Odoo module skeleton at path/name.

    Args:
        name: Module technical name, e.g. 'my_custom_module'
        path: Parent directory where the module folder will be created
    """
    module_dir = Path(path) / name
    if module_dir.exists():
        raise FileExistsError(f"Directory already exists: {module_dir}")

    created: list[str] = []

    def write(rel: str, content: str) -> None:
        target = module_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(content).lstrip())
        created.append(str(target.relative_to(module_dir)))

    write(
        "__manifest__.py",
        f"""\
        {{
            'name': '{name}',
            'version': '17.0.1.0.0',
            'category': 'Uncategorized',
            'summary': '',
            'depends': ['base'],
            'data': [],
            'installable': True,
            'auto_install': False,
            'license': 'LGPL-3',
        }}
        """,
    )

    write("__init__.py", "from . import models\n")
    write("models/__init__.py", "# import your models here\n")

    write(
        "security/ir.model.access.csv",
        "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n",
    )

    return {"module": name, "path": str(module_dir), "files_created": created}


# ---------------------------------------------------------------------------
# create_model_file
# ---------------------------------------------------------------------------

def create_model_file(
    module_path: str,
    model_name: str,
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Generate a Python model file inside an existing module.

    Args:
        module_path: Absolute path to the module root
        model_name:  Odoo model name, e.g. 'x_my_module.record'
        fields:      List of field dicts with keys: name, type, string,
                     and optionally: required, readonly, comodel_name, help
    """
    module_dir = Path(module_path)
    if not module_dir.exists():
        raise FileNotFoundError(f"Module path does not exist: {module_path}")

    class_name = _class_name(model_name)
    filename = _model_to_filename(model_name) + ".py"
    target = module_dir / "models" / filename

    lines: list[str] = [
        "from odoo import models, fields, api",
        "",
        "",
        f"class {class_name}(models.Model):",
        f"    _name = '{model_name}'",
        f"    _description = '{class_name}'",
        "",
    ]

    for f in fields:
        fname = f["name"]
        ftype = f.get("type", "char").lower()
        fclass = FIELD_TYPE_MAP.get(ftype, "fields.Char")
        attrs: list[str] = []

        if f.get("string"):
            attrs.append(f"string='{f['string']}'")
        if f.get("required"):
            attrs.append("required=True")
        if f.get("readonly"):
            attrs.append("readonly=True")
        if f.get("comodel_name"):
            attrs.append(f"comodel_name='{f['comodel_name']}'")
        if f.get("help"):
            attrs.append(f"help='{f['help']}'")

        attr_str = ", ".join(attrs)
        lines.append(f"    {fname} = {fclass}({attr_str})")

    lines.append("")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines))

    return {"model": model_name, "file": str(target)}


# ---------------------------------------------------------------------------
# create_view_inheritance
# ---------------------------------------------------------------------------

def create_view_inheritance(
    module_path: str,
    base_xmlid: str,
    fields_to_add: list[dict[str, Any]],
    position: str = "after",
    ref_field: str | None = None,
) -> dict[str, Any]:
    """
    Generate an XML view inheritance file.

    Args:
        module_path:   Absolute path to the module root
        base_xmlid:    The xmlid of the view to inherit, e.g. 'sale.view_order_form'
        fields_to_add: List of dicts with keys: name, widget (optional)
        position:      XPath position: 'after', 'before', 'inside', 'replace'
        ref_field:     Field name to use as XPath anchor (defaults to first field)
    """
    if "." not in base_xmlid:
        raise ValueError(f"base_xmlid must be 'module.id', got: '{base_xmlid}'")

    module_dir = Path(module_path)
    module_name = module_dir.name
    safe_id = base_xmlid.replace(".", "_")
    inherit_id = f"{module_name}.{safe_id}_inherit"

    anchor = ref_field or (fields_to_add[0]["name"] if fields_to_add else "name")

    indent = "                    "  # 20 spaces — inside <field name="anchor">
    field_lines: list[str] = []
    for f in fields_to_add:
        fname = f["name"]
        widget = f.get("widget", "")
        widget_attr = f' widget="{widget}"' if widget else ""
        field_lines.append(f'{indent}<field name="{fname}"{widget_attr}/>')

    fields_block = "\n".join(field_lines)

    xml_content = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<odoo>\n"
        f'    <record id="{inherit_id}" model="ir.ui.view">\n'
        f'        <field name="name">{base_xmlid}.inherit.{module_name}</field>\n'
        f'        <field name="model"><!-- TODO: set model name --></field>\n'
        f'        <field name="inherit_id" ref="{base_xmlid}"/>\n'
        f'        <field name="arch" type="xml">\n'
        f'            <field name="{anchor}" position="{position}">\n'
        f"{fields_block}\n"
        f'            </field>\n'
        f'        </field>\n'
        f'    </record>\n'
        f"</odoo>\n"
    )

    views_dir = module_dir / "views"
    views_dir.mkdir(exist_ok=True)
    out_file = views_dir / f"{safe_id}_inherit.xml"
    out_file.write_text(xml_content)

    return {
        "file": str(out_file),
        "inherit_id": inherit_id,
        "base_xmlid": base_xmlid,
        "fields_added": [f["name"] for f in fields_to_add],
    }

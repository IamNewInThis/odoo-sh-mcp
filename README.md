# odoo-sh-mcp

MCP server for Odoo SH that exposes **ORM metadata and framework introspection** to Claude Code via XML-RPC.

Unlike existing Odoo MCP servers that read business records (customers, invoices), this one reads the **framework itself**: model fields, view XML, installed modules, and server logs.

## What it does

```
Claude Code (your machine)
       ↓ MCP protocol (stdio)
odoo-sh-mcp (Python, local)
       ↓ XML-RPC
Odoo SH (remote instance)
```

No SSH. No direct DB access. Only the XML-RPC API Odoo already exposes.

## Tools

### Tier 1 — ORM introspection
| Tool | Description |
|------|-------------|
| `get_model_fields` | All fields for a model: type, label, required, relation, compute |
| `get_model_info` | Model metadata: description, modules, inherited models |
| `search_models` | Find models by partial name or description |

### Tier 2 — View inspection
| Tool | Description |
|------|-------------|
| `get_views` | Full XML arch of all views (or a specific type) for a model |
| `get_view_by_xmlid` | Resolve an xmlid and return its full arch |
| `find_field_in_view` | Find which views contain a field and at which line |

### Tier 3 — Local scaffold (no Odoo connection)
| Tool | Description |
|------|-------------|
| `scaffold_module` | Create a minimal module skeleton on disk |
| `create_model_file` | Generate a Python model file inside an existing module |
| `create_view_inheritance` | Generate an XML view inheritance file |

### Tier 4 — Module management
| Tool | Description |
|------|-------------|
| `list_modules` | List modules with state and version |
| `install_module` | Install a module via XML-RPC |
| `upgrade_module` | Upgrade an installed module via XML-RPC |

### Tier 5 — Logs
| Tool | Description |
|------|-------------|
| `get_server_logs` | Fetch recent server logs from `ir.logging` |

## Installation

```bash
# With uv (recommended)
uvx odoo-sh-mcp

# Or with pip
pip install odoo-sh-mcp
```

## Configuration

### Single instance

```bash
claude mcp add odoo-mycompany \
  --command uvx \
  --args odoo-sh-mcp \
  --env ODOO_URL=https://mycompany.odoo.com \
  --env ODOO_DB=mycompany \
  --env ODOO_API_KEY=your_key_here
```

### Multi-instance (`.claude/mcp.json`)

```jsonc
{
  "mcpServers": {
    "odoo-company-a": {
      "command": "uvx",
      "args": ["odoo-sh-mcp"],
      "env": {
        "ODOO_URL": "https://company-a.odoo.com",
        "ODOO_DB": "company-a",
        "ODOO_API_KEY": "xxx"
      }
    },
    "odoo-company-b": {
      "command": "uvx",
      "args": ["odoo-sh-mcp"],
      "env": {
        "ODOO_URL": "https://company-b.odoo.com",
        "ODOO_DB": "company-b",
        "ODOO_API_KEY": "yyy"
      }
    }
  }
}
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ODOO_URL` | Yes | Instance URL, e.g. `https://mycompany.odoo.com` |
| `ODOO_DB` | Yes | Database name |
| `ODOO_API_KEY` | Yes* | API key (Settings > Technical > API Keys) |
| `ODOO_USERNAME` | Yes* | email address for API key auth |
| `ODOO_PASSWORD` | No | Password if not using API key |

*API keys available in Odoo 14+. For older versions use `ODOO_USERNAME` + `ODOO_PASSWORD`.

## Development

```bash
git clone https://github.com/nicoruiz/odoo-sh-mcp
cd odoo-sh-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -e "." pytest pytest-asyncio
pytest tests/ -v
```

## License

MPL-2.0

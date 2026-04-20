# odoo-sh-mcp

MCP server for Odoo SH that gives Claude Code full access to your Odoo instance via XML-RPC: inspect the ORM, read and write business records, manage modules, and tail server logs.

## What it does

```
Claude Code (your machine)
       ↓ MCP protocol (stdio)
odoo-sh-mcp (Python, local)
       ↓ XML-RPC              ↓ SSH / SFTP
Odoo SH (remote instance) ←──────────────
```

Two transport layers:
- **XML-RPC** — ORM introspection, records, modules, logs (no SSH needed)
- **SSH / SFTP** — upload files directly to `~/src/user/`, run `odoo-update`, restart services, tail logs

## Tools

### Tier 1 — ORM introspection
| Tool | Description |
|------|-------------|
| `get_model_fields` | All fields for a model: type, label, required, relation, compute |
| `get_model_info` | Model metadata: description, modules, inherited models |
| `search_models` | Find models by partial name or description |
| `search_records` | Search and read records from any model |
| `create_record` | Create a new record in any model |
| `update_record` | Update fields of an existing record by ID |
| `delete_record` | Delete a record by ID |

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

### Tier 6 — SSH / Odoo.sh direct access
| Tool | Description |
|------|-------------|
| `ssh_exec` | Execute any shell command on the Odoo.sh server |
| `ssh_upload_file` | Upload a local file to `~/src/user/<module>/` via SFTP |
| `ssh_update_module` | Run `odoo-update <module>` on the server |
| `ssh_restart` | Restart Odoo.sh services via `odoosh-restart` |
| `ssh_read_log` | Tail `~/logs/odoo.log` from the server |

## Installation

```bash
# With uv (recommended)
uvx odoo-sh-mcp

# Or with pip
pip install odoo-sh-mcp
```

## Configuration

### Single instance (XML-RPC only)

```bash
claude mcp add odoo-mycompany uvx odoo-sh-mcp \
  -e ODOO_URL=https://mycompany.odoo.com \
  -e ODOO_DB=mycompany \
  -e ODOO_API_KEY=your_key_here \
  -e ODOO_USERNAME=you@mycompany.com
```

### Single instance (XML-RPC + SSH)

Includes Tier 6 SSH tools for direct file upload and server commands:

```bash
claude mcp add odoo-mycompany uvx odoo-sh-mcp \
  -e ODOO_URL=https://mycompany.odoo.com \
  -e ODOO_DB=mycompany \
  -e ODOO_API_KEY=your_key_here \
  -e ODOO_USERNAME=you@mycompany.com \
  -e ODOO_SH_SSH_HOST=mycompany-main-staging-31140548.dev.odoo.com \
  -e ODOO_SH_SSH_USER=31140548 \
  -e ODOO_SH_SSH_KEY=~/.ssh/id_ed25519
```

### Multi-instance

Run once per instance:

```bash
claude mcp add odoo-company-a uvx odoo-sh-mcp \
  -e ODOO_URL=https://company-a.odoo.com \
  -e ODOO_DB=company-a \
  -e ODOO_API_KEY=xxx \
  -e ODOO_USERNAME=you@company-a.com

claude mcp add odoo-company-b uvx odoo-sh-mcp \
  -e ODOO_URL=https://company-b.odoo.com \
  -e ODOO_DB=company-b \
  -e ODOO_API_KEY=yyy \
  -e ODOO_USERNAME=you@company-b.com
```

Or edit `.claude/mcp.json` directly:

```jsonc
{
  "mcpServers": {
    "odoo-company-a": {
      "command": "uvx",
      "args": ["odoo-sh-mcp"],
      "env": {
        "ODOO_URL": "https://company-a.odoo.com",
        "ODOO_DB": "company-a",
        "ODOO_API_KEY": "xxx",
        "ODOO_USERNAME": "you@company-a.com",
        "ODOO_SH_SSH_HOST": "company-a-main-staging-XXXXX.dev.odoo.com",
        "ODOO_SH_SSH_USER": "XXXXX",
        "ODOO_SH_SSH_KEY": "~/.ssh/id_ed25519"
      }
    },
    "odoo-company-b": {
      "command": "uvx",
      "args": ["odoo-sh-mcp"],
      "env": {
        "ODOO_URL": "https://company-b.odoo.com",
        "ODOO_DB": "company-b",
        "ODOO_API_KEY": "yyy",
        "ODOO_USERNAME": "you@company-b.com",
        "ODOO_SH_SSH_HOST": "company-b-main-staging-YYYYY.dev.odoo.com",
        "ODOO_SH_SSH_USER": "YYYYY",
        "ODOO_SH_SSH_KEY": "~/.ssh/id_ed25519"
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
| `ODOO_SH_SSH_HOST` | SSH only | Odoo.sh branch hostname, e.g. `mycompany-main-staging-XXXXX.dev.odoo.com` |
| `ODOO_SH_SSH_USER` | SSH only | Odoo.sh build ID shown in the SSH command |
| `ODOO_SH_SSH_KEY` | SSH only | Path to your private SSH key (default `~/.ssh/id_ed25519`) |

*API keys available in Odoo 14+. For older versions use `ODOO_USERNAME` + `ODOO_PASSWORD`.

### SSH setup (Tier 6 tools)

SSH tools let Claude upload files and run commands directly on the Odoo.sh server, bypassing git commits for fast iteration.

**1. Generate an SSH key (if you don't have one)**

<details>
<summary>macOS / Linux</summary>

```bash
ssh-keygen -t ed25519 -C "your-name-odoo-sh"
```

Press Enter to accept the default path (`~/.ssh/id_ed25519`).

</details>

<details>
<summary>Windows</summary>

Open **PowerShell** or **Git Bash** and run:

```powershell
ssh-keygen -t ed25519 -C "your-name-odoo-sh"
```

The key is saved to `C:\Users\YourName\.ssh\id_ed25519`. In the `.env` use forward slashes to avoid escape issues:

```env
ODOO_SH_SSH_KEY=C:/Users/YourName/.ssh/id_ed25519
```

> Windows 10/11 include OpenSSH by default. If `ssh-keygen` is not found, enable it via **Settings → Apps → Optional Features → OpenSSH Client**.

</details>

**2. Add your public key to Odoo.sh**

Go to `https://www.odoo.sh` → click your avatar (top right) → **Change My Profile** → **SSH Keys** → paste the output of:

```bash
# macOS / Linux
cat ~/.ssh/id_ed25519.pub

# Windows (PowerShell)
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
```

> Odoo.sh only accepts `ssh-rsa` and `ssh-ed25519` keys.

**3. Load your key into the SSH agent**

<details>
<summary>macOS</summary>

```bash
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

This saves the passphrase to the macOS Keychain so you never have to re-enter it.

</details>

<details>
<summary>Linux</summary>

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

</details>

<details>
<summary>Windows</summary>

Enable and start the SSH agent service (run PowerShell as Administrator):

```powershell
Set-Service -Name ssh-agent -StartupType Automatic
Start-Service ssh-agent
ssh-add "$env:USERPROFILE\.ssh\id_ed25519"
```

</details>

**4. Find your branch SSH host**

In the Odoo.sh dashboard, click your branch → **Connect** → copy the SSH command. It looks like:

```
ssh 31140548@mycompany-main-staging-31140548.dev.odoo.com
```

The number before `@` is the `ODOO_SH_SSH_USER`, the hostname after is `ODOO_SH_SSH_HOST`.

**5. Add to your `.env` or MCP config**

```env
ODOO_SH_SSH_HOST=mycompany-main-staging-31140548.dev.odoo.com
ODOO_SH_SSH_USER=31140548
ODOO_SH_SSH_KEY=~/.ssh/id_ed25519
```

Then use the full `claude mcp add` command from the [Single instance (XML-RPC + SSH)](#single-instance-xml-rpc--ssh) section above.

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

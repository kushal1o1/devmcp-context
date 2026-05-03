# Installation

## Prerequisites

- Python 3.12 or higher
- `uv` package manager (recommended) or `pip`

## Install uv

If you don't have `uv` installed, install it first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, restart your terminal so `uv` is in your PATH.

Verify installation:
```bash
uv --version
```

## Install devmcp-context

### Option 1: From GitHub (Recommended)

```bash
git clone https://github.com/kushal1o1/devmcp-context.git
cd devmcp-context
uv sync
```

This installs the project and all dependencies in an isolated virtual environment.

### Option 2: From PyPI

Once published to PyPI:

```bash
pip install devmcp-context
```

### Option 3: Development Installation

If you want to modify or contribute to devmcp-context:

```bash
git clone https://github.com/kushal1o1/devmcp-context.git
cd devmcp-context
uv sync --all-extras
```

The `--all-extras` flag installs development dependencies including testing and linting tools.

```mermaid
graph TD
    Start["Install<br/>devmcp-context"]
    Dev{"Is this for<br/>development?"}
    PyPI["From PyPI<br/>(pip install)"]
    GitHub["From GitHub<br/>(git clone)"]
    DevSetup["Dev Setup<br/>(uv sync --all-extras)"]
    ProdSetup["Production Setup<br/>(uv sync)"]
    Done["Ready to Use"]
    
    Start --> Dev
    Dev -->|No| PyPI
    Dev -->|Yes| GitHub
    Dev -->|Yes<br/>Source| GitHub
    GitHub --> DevSetup
    PyPI --> Done
    DevSetup --> Done
    GitHub -->|Source Only| ProdSetup
    ProdSetup --> Done
    
    style Start fill:#f0f0f0
    style Dev fill:#ffe8e8
    style PyPI fill:#e8e8ff
    style GitHub fill:#e8f0ff
    style DevSetup fill:#e8f0ff
    style ProdSetup fill:#e8f0ff
    style Done fill:#e8ffe8
```

## Verify Installation

Test that everything works:

```bash
uv run devmcp-context --help
```

You should see the server name and available MCP tools listed.

## Next Steps

- [Quick Start](quickstart.md) — Start using devmcp-context in minutes
- [Usage Guide](usage.md) — Learn the complete workflow
- [Deployment](deployment.md) — Integrate with your agent

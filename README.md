# devmcp-context

[![PyPI version](https://img.shields.io/pypi/v/devmcp-context.svg)](https://pypi.org/project/devmcp-context/)
[![Python](https://img.shields.io/pypi/pyversions/devmcp-context.svg)](https://pypi.org/project/devmcp-context/)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)

<p align="center">
	<img src="https://github.com/kushal1o1/devmcp-context/blob/main/static/logo.png?raw=true" alt="devmcp-context logo" width="420" />
</p>

Structured AI memory layer. A single source of truth for what your agent knows across conversations.

`devmcp-context` is a Model Context Protocol (MCP) server that provides persistent, organized memory for AI agents. Your agent's memory is now **visible, editable, and searchable** — without retraining.

Published on PyPI: [https://pypi.org/project/devmcp-context/](https://pypi.org/project/devmcp-context/)

## The Problem

AI agents are black boxes. You can't see what they remember. When they forget something important or remembers something wrong, you're stuck.

**devmcp-context changes this.** Your agent's memory is now:
- **Visible** — Plain text files in your project folder
- **Editable** — Change any entry, agent sees it immediately  
- **Structured** — Organized into 5 categories with automatic cleanup
- **Persistent** — Survives across agent sessions and restarts
- **Recall-first** — Memory loads automatically at session start

## Installation

```bash
pip install devmcp-context
```

Or with uv:

```bash
uv add devmcp-context
```

## Quick Start

Register in your agent's MCP config (Claude, Node.js, Python, Docker), then:

```bash
devmcp-context
```

Your agent will auto-discover the memory server. At session start, it calls `context_session_start` to load what it already knows.

## Features

- **Auto-recall at session start** — project + decisions memory loaded automatically, compact index of everything else
- 5 memory categories (project, decisions, errors, tasks, ephemeral)
- **Outcome tracking** — `what_worked` and `what_failed` fields for decisions and errors
- **Superseded entries** — redirect recall to newer entries instead of deleting history
- **Key fact first** — entry summaries lead with the most important line
- Automatic expiration (TTL) — errors expire in 30 days, tasks in 14
- Full-text search across all entries
- Tagging system for organization
- Persistent file-based storage (no database)
- Session recall metric — tracks whether memory was used before edits
- MCP-compliant server

## Documentation

Full docs: [https://kushal1o1.github.io/devmcp-context/](https://kushal1o1.github.io/devmcp-context/)

- Getting Started guide
- Installation instructions
- API Reference (8 tools)
- Memory categories explained
- Architecture diagrams (Mermaid)
- Deployment guide
- Development guide

## Usage Example

In your agent prompt:

```
Agent calls context_session_start first to load memory.

Use context_save to remember insights:
- save("decisions", "auth_strategy", "Use JWT with refresh tokens",
       tags=["security"],
       what_worked="Stateless, scales horizontally",
       what_failed="Token refresh is complex")

Use context_load to retrieve memories:
- load("decisions")

Use context_search to find specific memories:
- search("JWT")

Use superseded_by to redirect old entries:
- save("decisions", "new-auth", "Switched to OAuth2",
       superseded_by="old-auth")
```

## License

MIT — See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](docs/contributing.md) for guidelines.

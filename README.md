# devmcp-context

<p align="center">
	<img src="https://github.com/kushal1o1/devmcp-context/blob/main/static/logo.png?raw=true" alt="devmcp-context logo" width="420" />
</p>

Structured AI memory layer. A single source of truth for what your agent knows across conversations.

`devmcp-context` is a Model Context Protocol (MCP) server that provides persistent, organized memory for AI agents. Your agent's memory is now **visible, editable, and searchable** — without retraining.

## The Problem

AI agents are black boxes. You can't see what they remember. When they forget something important or remember something wrong, you're stuck.

**devmcp-context changes this.** Your agent's memory is now:
- **Visible** — Plain text files in your project folder
- **Editable** — Change any entry, agent sees it immediately  
- **Structured** — Organized into 5 categories with automatic cleanup
- **Persistent** — Survives across agent sessions and restarts

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

Your agent will auto-discover the memory server. Start asking questions, and memories are saved to `ai-context/` folder.

## Features

- 5 memory categories (project, decisions, errors, tasks, ephemeral)
- Automatic expiration (TTL) — errors expire in 30 days, tasks in 14
- Full-text search across all entries
- Tagging system for organization
- Persistent file-based storage (no database)
- MCP-compliant server

## Documentation

Full docs: [https://kushal1o1.github.io/devmcp-context/](https://kushal1o1.github.io/devmcp-context/)

- Getting Started guide
- Installation instructions
- API Reference (6 tools)
- Memory categories explained
- Architecture diagrams (Mermaid)
- Deployment guide
- Development guide

## Usage Example

In your agent prompt:

```
Use context_save to remember insights:
- save("decisions", "auth_strategy", "Use JWT with refresh tokens", tags=["security"])

Use context_load to retrieve memories:
- load("decisions")

Use context_search to find specific memories:
- search("JWT")
```

## License

MIT — See LICENSE for details.

## Contributing

Contributions welcome! See CONTRIBUTING.md for guidelines.

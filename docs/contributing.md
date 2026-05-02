# Contributing

Thank you for your interest in contributing to context-mcp.

## How to Contribute

### Reporting Bugs

Open a GitHub issue with:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

### Suggesting Features

Open a GitHub issue with:
- Use case and motivation
- Proposed solution
- Alternative approaches considered

### Submitting Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/description`)
3. Make your changes
4. Ensure tests pass: `uv run pytest tests/ -v`
5. Run linter: `uv run ruff check src/ tests/`
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request

### Improving Documentation

Documentation improvements are always welcome:
1. Fork the repository
2. Edit files in `docs/`
3. Build locally: `uv run mkdocs serve`
4. Verify changes look good
5. Submit PR

## Development Workflow

See the [Development Guide](development.md) for setup instructions.

Quick start:

```bash
git clone https://github.com/kushal1o1/context-mcp.git
cd context-mcp
uv sync --all-extras
uv run pytest tests/ -v
```

## Code Standards

- Follow PEP 8 style guide
- Type hints for all functions
- Clear docstrings
- Tests for new code
- No external service dependencies

Ruff will check compliance automatically.

## Testing

All tests must pass:

```bash
uv run pytest tests/ -v
```

Add tests for new features:
- Unit tests in `tests/test_*.py`
- Use descriptive test names
- Include docstrings

Target 90%+ code coverage.

## Commit Messages

Use clear, descriptive commit messages:

Good:
- "Add context_search tool for full-text search"
- "Fix TTL calculation for expired entries"
- "Update documentation for deployment"

Avoid:
- "Fix bug"
- "Update stuff"
- "WIP"

## Community

Be respectful and constructive in all interactions.

Everyone is welcome regardless of experience level.

## License

By contributing, you agree your code will be licensed under the MIT License.

## Questions?

Open a GitHub Discussion or issue. We're here to help.

Thank you for contributing!

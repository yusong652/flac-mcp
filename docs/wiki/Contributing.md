# Contributing

This page summarizes the checks expected before contributing changes to `flac-mcp`.

## Development Setup

From repository root:

```powershell
uv sync
uv sync --group dev
```

Run the MCP server locally:

```powershell
uv run flac-mcp
```

## Core Checks

Run:

```powershell
$env:UV_CACHE_DIR=(Join-Path (Get-Location) ".uv-cache")
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run mypy src
uv run pytest tests/test_phase2_tools.py tests/test_tool_contracts.py
uv run pytest tests/test_versioned_schema.py tests/test_docs_tool_contracts.py
```

## Command Documentation Checks

After changing command docs:

```powershell
uv run python scripts/generate_flac_command_index.py --check
uv run python scripts/validate_flac_command_docs.py
```

## Runtime Validation

When a change affects execution behavior, validate against real FLAC software:

1. Start the FLAC GUI.
2. Run `addon.py` inside FLAC.
3. Call `flac_get_runtime_info`.
4. Call `flac_validate_runtime`.
5. Run the smallest relevant command smoke test.

Record the product, version, dimension, commands tested, and outcome.

## Pull Request Checklist

Before opening or updating a PR:

- Keep MCP-side code and bridge-side code separate.
- Keep tool responses in the unified `ok/data/error` envelope.
- Pass explicit `product` and `version` in docs-tool tests when behavior is product/version-sensitive.
- Avoid committing local paths, usernames, machine-specific project names, or temporary validation files.
- Prefer structured data changes over ad-hoc text parsing.
- Keep generated or bulk documentation diffs explainable.

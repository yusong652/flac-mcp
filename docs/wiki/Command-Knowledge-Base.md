# Command Knowledge Base

The command knowledge base lets agents browse and search FLAC command documentation without guessing command syntax.

## Tools

Use `flac_browse_commands` when the command path is known or when exploring a category:

```text
flac_browse_commands(command="zone", product="flac3d", version="9.7")
flac_browse_commands(command="zone fluid", product="flac3d", version="9.7")
```

Use `flac_query_command` when the command path is not known:

```text
flac_query_command(query="unsaturated fluid", product="flac3d", version="9.7")
flac_query_command(query="zone create", product="flac2d", version="9.7")
```

## Product Filtering

Always pass `product` when the active runtime is known:

```text
product="flac2d"
product="flac3d"
```

This prevents FLAC3D-only commands from being suggested for FLAC2D and prevents FLAC2D-specific commands from being suggested for FLAC3D.

## Version Filtering

Always pass `version` for version-sensitive work:

```text
version="6.0"
version="7.0"
version="9.7"
```

FLAC2D 6.0 and 7.0 are not applicable in the bundled documentation matrix.

## Command Coverage vs API Coverage

Command coverage answers:

```text
Are bundled FLAC command docs available for this product/version?
```

Python API coverage answers:

```text
Are bundled Python SDK API docs available for this product/version?
```

These are separate because FLAC command syntax and Python SDK APIs are different interfaces.

## Maintenance

Command docs live under:

```text
src/flac_mcp/knowledge/resources/command_docs/
```

After changing command docs:

```powershell
uv run python scripts/generate_flac_command_index.py --check
uv run python scripts/validate_flac_command_docs.py
```

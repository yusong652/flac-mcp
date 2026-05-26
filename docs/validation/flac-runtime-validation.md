# FLAC Runtime Validation

This release-time check validates a live FLAC GUI process through the bridge without adding MCP tools.

Start the bridge from FLAC first, then run from the repository root:

```powershell
uv run python scripts/validate_runtime.py --bridge-url ws://localhost:9002
```

The default check is non-destructive. It verifies runtime identity, simple command execution, and temporary `.dat` file write/read/delete behavior.

Use JSON output for CI logs or release records:

```powershell
uv run python scripts/validate_runtime.py --json
```

Only use the destructive reset check in a disposable model:

```powershell
uv run python scripts/validate_runtime.py --include-model-reset
```

Expected successful summary:

```json
{
  "status": "passed",
  "failed": 0
}
```

Validate at least these targets before claiming runtime coverage:

- FLAC2D 9.0
- FLAC3D 6.0
- FLAC3D 7.0
- FLAC3D 9.0

Do not expose this as an MCP tool. Agents can already compose runtime checks through `flac_execute_code`; this script exists for release-time self-checks and reproducible validation notes.

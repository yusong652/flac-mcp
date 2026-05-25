# FLAC Runtime Validation Checklist

Use this checklist when validating `flac-mcp` against real FLAC software.

## Supported Targets

Validate these product/version combinations:

- FLAC2D 9.0
- FLAC3D 6.0
- FLAC3D 7.0
- FLAC3D 9.0

FLAC2D 6.0 and 7.0 are not applicable in this project's bundled documentation matrix.

## Local Preflight

Run these from the repository root before opening FLAC:

```powershell
$env:UV_CACHE_DIR=(Join-Path (Get-Location) '.uv-cache')
uv run ruff check
uv run pytest
uv run mypy src
```

Confirm documentation coverage:

```text
flac_command_coverage
flac_python_api_coverage
```

Expected high-level command coverage:

```text
flac2d 6.0 applicable=False
flac2d 7.0 applicable=False
flac2d 9.0 applicable=True complete=True
flac3d 6.0 applicable=True complete=False
flac3d 7.0 applicable=True complete=False
flac3d 9.0 applicable=True complete=True
```

## Bridge Startup

For each target runtime:

1. Open the intended FLAC GUI.
2. Run `addon.py` inside the FLAC IPython console.
3. Confirm the bridge reports `ws://localhost:9002`.
4. Restart the MCP client if it was already open.

If `9002` is already in use, set `FLAC_MCP_BRIDGE_PORT` before launching FLAC and point the MCP server at the same port with `--bridge-url` or `FLAC_MCP_BRIDGE_URL`.

## Runtime Identity

Call `flac_get_runtime_info`.

Expected:

- FLAC2D 9.0: `product=flac2d`, `dimension=2`, `flac_version=9.0`
- FLAC3D 6.0: `product=flac3d`, `dimension=3`, `flac_version=6.0`
- FLAC3D 7.0: `product=flac3d`, `dimension=3`, `flac_version=7.0`
- FLAC3D 9.0: `product=flac3d`, `dimension=3`, `flac_version=9.0`

If product or dimension is wrong, stop. The bridge is attached to the wrong GUI.

## Documentation Guards

These should fail with structured errors:

```text
flac_browse_commands(command="model new", product="flac2d", version="7.0")
flac_query_command(query="model new", product="flac2d", version="7.0")
flac_browse_python_api(api="itasca", product="flac2d", version="7.0")
flac_query_python_api(query="zone", product="flac2d", version="7.0")
```

Expected error code:

```text
product_version_not_applicable
```

These should also fail:

```text
flac_browse_commands(command="zone create2d", product="flac3d", version="9.0")
flac_browse_python_api(api="itasca.gravity_z", product="flac2d", version="9.0")
flac_browse_reference(topic="range-elements position-z", product="flac2d", version="9.0")
```

Expected error codes:

```text
command_unavailable_for_product
api_unavailable_for_product
item_unavailable_for_product
```

## Execution Smoke Test

Call `flac_execute_code`:

```python
import itasca as it
print("FLAC bridge online")
print(it.command("model new"))
print(it.command("model list information"))
```

Expected:

- `ok=true`
- stdout contains `FLAC bridge online`
- no bridge disconnect

## Product-Specific Smoke Tests

For FLAC2D 9.0:

```python
import itasca as it
print(it.command("model new"))
print(it.command("zone create2d quad size 1 1"))
print(it.command("model list information"))
```

For FLAC3D 6.0/7.0/9.0:

```python
import itasca as it
print(it.command("model new"))
print(it.command("zone create brick size 1 1 1"))
print(it.command("model list information"))
```

If syntax differs by installed version, record the exact error output and update the bundled command docs or version guard before treating the runtime as validated.

## Task Lifecycle Smoke Test

Create a small Python script in a real FLAC-accessible path and submit it with `flac_execute_task`.

Minimal script:

```python
import itasca as it

it.command("model new")
it.command("model cycle 1")
print("task smoke complete")
```

Then verify:

```text
flac_check_task_status(task_id=<returned id>)
flac_list_tasks()
```

Expected:

- task reaches completed/success status
- captured output contains `task smoke complete`
- `flac_list_tasks` includes the task id

## Record Results

For each target, record:

- FLAC product/version
- `flac_get_runtime_info` payload
- bridge package version from FLAC console
- command/API/reference guard results
- execution smoke result
- task lifecycle result
- any command syntax differences found in real FLAC

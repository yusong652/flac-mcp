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
flac3d 6.0 applicable=True complete=True
flac3d 7.0 applicable=True complete=True
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

Then call `flac_validate_runtime` with default arguments.

Expected:

- `summary.status=passed`
- checks include `runtime_identity`, `command_execution`, and `dat_file_write`
- `summary.destructive_checks_enabled=false`

Only enable `include_model_reset=true` when it is acceptable for the validation
to run `model new` in the active FLAC session.

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
print(it.command("model large-strain off"))
print(it.command("zone create2d quadrilateral size 1 1"))
print(it.command("model list information"))
```

For FLAC3D 6.0/7.0/9.0:

```python
import itasca as it
print(it.command("model new"))
print(it.command("model large-strain off"))
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
it.command("model large-strain off")
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

## Recorded Validation Results

### 2026-05-26: FLAC3D 9.0

Environment observed through `flac_validate_runtime`:

- `product=flac3d`
- `dimension=3`
- `flac_version=9.0`
- embedded Python `3.10.5`

Passed checks:

- `flac_validate_runtime` default checks: `runtime_identity`, `command_execution`, and `dat_file_write`
- `flac_validate_runtime(include_model_reset=true)`
- 3D model creation and cycling:
  - `model new`
  - `model large-strain off`
  - `zone create brick size 1 1 1`
  - `zone cmodel assign elastic`
  - `zone property bulk 1e8 shear 5e7`
  - `model cycle 1`
- Python object API:
  - `it.zone.list()`
  - `it.gridpoint.list()`
  - zone/gridpoint positions return 3D coordinates
- Array API:
  - `it.zonearray.pos()` returned shape `[4, 3]` in the validation model
  - `it.gridpointarray.pos()` returned shape `[18, 3]`
- `.dat` workflow:
  - MCP-created `.dat` file can be executed with `program call`
  - validation `.dat` created two zones and was cleaned up
- Boundary-condition workflow:
  - `zone face skin`
  - `zone gridpoint fix velocity-z range position-z 0`
  - `zone face apply stress-normal -1e5 range group 'Top'`
  - `zone initialize density 2000`
  - `model gravity 0 0 -9.81`
  - `model cycle 2`
- Task lifecycle:
  - `flac_execute_task`
  - `flac_check_task_status`
  - `flac_list_tasks`
  - `flac_interrupt_task`
- Task output pagination and captured task result fields

Issues found and resolved:

- `model cycle` requires `model large-strain on/off` first in the tested runtime.
- Gravity cycling requires zone density before `model cycle`.
- Array APIs are exposed as attributes on the `itasca` extension module at runtime. Use `import itasca as it; it.zonearray.pos()`, not `import itasca.zonearray`.

### 2026-05-26: FLAC2D 9.0

Environment observed through `flac_validate_runtime`:

- `product=flac2d`
- `dimension=2`
- `flac_version=9.0`
- embedded Python `3.10.5`

Passed checks:

- `flac_validate_runtime` default checks: `runtime_identity`, `command_execution`, and `dat_file_write`
- `flac_validate_runtime(include_model_reset=true)`
- `flac_validate_runtime(keep_artifacts=true)` keeps the validation `.dat` file; manual cleanup succeeded
- 2D model creation and cycling:
  - `model new`
  - `model large-strain off`
  - `zone create2d quadrilateral size 2 2`
  - `zone cmodel assign elastic`
  - `zone property bulk 1e8 shear 5e7`
  - `model cycle 1`
- Python object API:
  - `it.zone.list()`
  - `it.gridpoint.list()`
  - zone/gridpoint positions return 2D coordinates
- Array API:
  - `it.zonearray.pos()` returned shape `[4, 2]`
  - `it.gridpointarray.pos()` returned shape `[9, 2]`
- `.dat` workflow:
  - MCP-created `.dat` file can be executed with `program call`
  - validation `.dat` created two zones and was cleaned up
- Boundary-condition workflow:
  - `zone face skin`
  - `zone gridpoint fix velocity-y range position-y 0`
  - `zone face apply stress-normal -1e5 range group 'Top'`
  - `zone initialize density 2000`
  - `model gravity 0 -9.81`
  - `model cycle 2`
- Task lifecycle:
  - `flac_execute_task`
  - `flac_check_task_status`
  - `flac_list_tasks`
  - `flac_interrupt_task`
- Task output pagination:
  - `limit`
  - `skip_newest`
  - `filter`
- Error-path behavior:
  - Python exceptions return structured `ok=false`
  - invalid FLAC commands return structured `ok=false` with FLAC expected-token text
  - timeout returns `code=timeout`
  - bridge recovered after timeout
- Documentation guards matched real FLAC2D behavior:
  - `zone create` is filtered out for `product=flac2d`
  - `zone create2d` is available for `product=flac2d`
  - `itasca.gravity_z` is unavailable for `product=flac2d`
  - `range-elements position-z` is unavailable for `product=flac2d`
  - `range-elements position-y` is available for `product=flac2d`

Issues found and resolved:

- FLAC2D 9.0 uses `zone create2d quadrilateral ...`; `quad` is not the validated spelling.
- Real FLAC2D rejects z-direction commands such as `velocity-z` and `position-z`.
- Array APIs follow active product dimension at runtime: FLAC2D returns two columns for position/vector arrays; FLAC3D returns three.
- Large Python API module browsing can exceed the MCP response budget if full module docs are embedded in summary; module browsing now returns lightweight module metadata and function names, with detailed docs available from specific function paths such as `itasca.zonearray.pos`.

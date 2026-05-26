# Runtime Validation

Runtime validation confirms that the MCP server is connected to the intended FLAC GUI and that execution tools can safely interact with the active model.

## Basic Runtime Identity

Start with:

```text
flac_get_runtime_info
```

Check:

- `product`
- `dimension`
- `flac_version`
- `python_version`
- `python_executable`

Stop if the product or dimension does not match the FLAC GUI you intended to use.

## Non-Destructive Validation

Use:

```text
flac_validate_runtime
```

Expected high-level result:

```text
summary.status = passed
```

The default validation should include:

- bridge connectivity
- runtime identity
- safe command execution
- temporary `.dat` file write/read behavior

By default it should not reset the model. Only enable reset-style checks when it is acceptable to run `model new`.

## Manual Command Smoke Test

For a direct check through `flac_execute_code`:

```python
import itasca as it

print("FLAC bridge online")
it.command("model list information")
```

## Version-Sensitive Workflows

For version-sensitive workflows, validate both documentation and runtime:

```text
flac_browse_commands(command="model configure", product="flac3d", version="9.7")
flac_browse_commands(command="zone fluid", product="flac3d", version="9.7")
```

Then run the smallest practical FLAC command smoke test in the GUI before generating longer simulation scripts.

## Validation Record Template

Use this format when adding runtime validation notes:

```text
Date:
Product:
FLAC version:
Dimension:
Bridge URL:
Commands tested:
Result:
Notes:
```

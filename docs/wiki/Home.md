# flac-mcp Wiki

`flac-mcp` connects AI agents to ITASCA FLAC through the Model Context Protocol. It provides documentation tools for command/API/reference lookup and execution tools that operate through a bridge running inside the FLAC GUI.

## Architecture

`flac-mcp` has two runtime contexts:

- MCP server: normal Python environment, installed or launched with `uvx flac-mcp`.
- FLAC bridge: FLAC embedded Python, started inside FLAC GUI with `addon.py`.

The MCP server can browse bundled documentation without a running FLAC process. Execution tools require the bridge because only FLAC embedded Python can import `itasca` and operate on the active model.

## Main Pages

- [Installation](Installation.md)
- [Runtime Validation](Runtime-Validation.md)
- [Version Support Matrix](Version-Support-Matrix.md)
- [Command Knowledge Base](Command-Knowledge-Base.md)
- [Fluid Flow and Unsaturated Flow](Fluid-Flow-and-Unsaturated-Flow.md)
- [Contributing](Contributing.md)

## Quick Start

1. Register the MCP server in your MCP client with `uvx flac-mcp`.
2. Start FLAC GUI.
3. Run `addon.py` inside the FLAC IPython console.
4. Call `flac_get_runtime_info`.
5. Call `flac_validate_runtime`.
6. Use documentation tools with explicit `product` and `version` values.

## Recommended Agent Contract

Before generating or executing FLAC commands, an agent should know:

```text
target_product = flac2d | flac3d
target_version = 6.0 | 7.0 | 9.0 | 9.1 | 9.2 | 9.3 | 9.4 | 9.5 | 9.6 | 9.7
```

For product-sensitive queries, pass both values:

```text
flac_browse_commands(product=target_product, version=target_version)
flac_query_command(product=target_product, version=target_version)
flac_browse_python_api(product=target_product, version=target_version)
flac_query_python_api(product=target_product, version=target_version)
```

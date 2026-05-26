# Installation

This page covers the normal user setup for `flac-mcp`.

## Requirements

- ITASCA FLAC installed.
- `uv` installed.
- An MCP client such as Codex, Claude Code, Gemini CLI, GitHub Copilot CLI, OpenCode, or another MCP-capable client.

## Register the MCP Server

Use `uvx` from your normal Python environment:

```json
{
  "mcpServers": {
    "flac-mcp": {
      "command": "uvx",
      "args": ["flac-mcp"]
    }
  }
}
```

Documentation tools are available as soon as the MCP server starts.

## Start the FLAC Bridge

Execution tools require the bridge inside FLAC GUI.

1. Open the intended FLAC GUI.
2. Run `addon.py` inside the FLAC IPython console.
3. Confirm that the bridge reports a WebSocket URL.

The default bridge URL is:

```text
ws://localhost:9002
```

If that port is unavailable, start the bridge on another port and configure the MCP server with `--bridge-url` or `FLAC_MCP_BRIDGE_URL`.

## Verify the Setup

Call:

```text
flac_get_runtime_info
```

Confirm:

- product is `flac2d` or `flac3d`
- dimension matches the open FLAC GUI
- embedded Python is reachable

Then call:

```text
flac_validate_runtime
```

For a manual REPL check:

```python
import itasca as it
print("FLAC bridge online")
print(it.command("model list information"))
```

## Daily Startup

After first-time setup, each new FLAC session normally only needs:

1. Open FLAC GUI.
2. Start `addon.py`.
3. Restart or reconnect the MCP client if needed.

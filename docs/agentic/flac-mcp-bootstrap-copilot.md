# flac-mcp Bootstrap (GitHub Copilot CLI)

Use this profile when the client is GitHub Copilot CLI.

## Step 1 (GitHub Copilot CLI) - Configure MCP

[AGENT]

Default target: workspace `.mcp.json`.
Use user-level `~/.copilot/mcp-config.json` only if user explicitly asks for global sharing.

Add/merge this MCP entry:

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

If `uvx` is unavailable, fallback to:

```json
{
  "mcpServers": {
    "flac-mcp": {
      "command": "uv",
      "args": ["tool", "run", "flac-mcp"]
    }
  }
}
```

[USER ACTION REQUIRED]

Always close and restart the Copilot CLI session before continuing. Exit the current session and start a new one.

Verify at the end of bootstrap with `flac_get_runtime_info` and `flac_execute_code`.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/flac-mcp-bootstrap.md`

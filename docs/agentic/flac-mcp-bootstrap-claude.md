# flac-mcp Bootstrap (Claude Code)

Use this profile when the client uses `.mcp.json` style MCP config.

For Codex, use `docs/agentic/flac-mcp-bootstrap-codex.md` instead.

## Step 1 (Claude Code) - Configure MCP

[AGENT]

Default target: workspace `.mcp.json`.
Use user-level MCP config only if user explicitly asks for global sharing.

Add/merge this MCP entry:

```json
{
  "mcpServers": {
    "flac-mcp": {
      "type": "stdio",
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
      "type": "stdio",
      "command": "uv",
      "args": ["tool", "run", "flac-mcp"]
    }
  }
}
```

[USER ACTION REQUIRED]

Always close and reopen the Claude Code session before continuing.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/flac-mcp-bootstrap.md`

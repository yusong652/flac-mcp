# flac-mcp Bootstrap (toyoura-nagisa)

Use this profile when the client is toyoura-nagisa.

## Step 1 (toyoura-nagisa) - Configure MCP

[AGENT]

Preferred target: user-level `~/.nagisa/mcp_servers.json` (available across all working directories).
Fall back to workspace-level `./.nagisa/mcp_servers.json` only if the user-scope config is unavailable or write-blocked.

Add/merge this entry under `mcpServers`:

```json
{
  "mcpServers": {
    "flac-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["flac-mcp"],
      "enabled": true,
      "description": "FLAC MCP server"
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
      "args": ["tool", "run", "flac-mcp"],
      "enabled": true,
      "description": "FLAC MCP server"
    }
  }
}
```

Do not overwrite unrelated MCP servers in the same file.

[USER ACTION REQUIRED]

Always close and reopen the toyoura-nagisa session (or restart backend process) before continuing.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/flac-mcp-bootstrap.md`

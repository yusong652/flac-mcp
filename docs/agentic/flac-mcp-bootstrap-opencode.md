# flac-mcp Bootstrap (OpenCode)

Use this profile when the client is OpenCode.

## Step 1 (OpenCode) - Configure MCP

[AGENT]

Default target: workspace-level config `<workspace>/opencode.json`.
Use global config `~/.config/opencode/opencode.json` only if user explicitly asks for global sharing.
Prefer editing the workspace-relative file `./opencode.json` directly to avoid absolute-path mistakes.

Add/merge this MCP entry:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "flac-mcp": {
      "type": "local",
      "command": ["uvx", "flac-mcp"],
      "enabled": true
    }
  }
}
```

If `uvx` is unavailable, fallback to:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "flac-mcp": {
      "type": "local",
      "command": ["uv", "tool", "run", "flac-mcp"],
      "enabled": true
    }
  }
}
```

Optional verification:

```bash
opencode mcp list
```

Confirm `flac-mcp` is listed and enabled.

[USER ACTION REQUIRED]

Always close and reopen the OpenCode session before continuing.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/flac-mcp-bootstrap.md`

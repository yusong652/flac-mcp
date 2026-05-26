# flac-mcp

[English](https://github.com/yusong652/flac-mcp/blob/main/README.md) | [简体中文](https://github.com/yusong652/flac-mcp/blob/main/README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/flac-mcp)](https://pypi.org/project/flac-mcp/)
[![Downloads](https://static.pepy.tech/badge/flac-mcp)](https://pepy.tech/project/flac-mcp)
[![GitHub stars](https://img.shields.io/github/stars/yusong652/flac-mcp)](https://github.com/yusong652/flac-mcp/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

`flac3d>model new ;now, with LLM.`

**flac-mcp** connects AI agents to [ITASCA FLAC](https://www.itascacg.com/software/flac3d) through the [Model Context Protocol](https://modelcontextprotocol.io/) — browse documentation, run simulations, and execute code, all through natural conversation.

`flac3d>model solve ;LLM solves.`

## Tools (14)

**7 documentation tools** — browse and search FLAC commands, Python API, reference docs, and audit bundled command/Python API coverage. No bridge required.

**7 execution tools** — runtime inspection, runtime validation, interactive REPL, task submission, progress monitoring, interruption, and history. Requires bridge.

## How It Runs

`flac-mcp` has two processes:

- The MCP server runs on your normal Python environment through `uvx flac-mcp`.
- The bridge runs inside FLAC's embedded Python through [`addon.py`](addon.py) and listens on `ws://localhost:9002`.

Documentation tools work as soon as the MCP server is registered. Execution tools connect through the bridge, because only FLAC's embedded Python can `import itasca` and operate on the active model. Use `flac_get_runtime_info` at the start of a session to detect FLAC2D/FLAC3D, model dimension, and embedded Python details.

## First-time Setup

### Prerequisites

- **ITASCA FLAC 6.0, 7.0, or 9.0** installed
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** installed (for `uvx`)

### Agentic Setup (Recommended)

Copy this to your AI agent and let it self-configure. Include your target product/version when you know it:

```text
Fetch and follow this bootstrap guide end-to-end:
https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap.md

Target runtime: FLAC2D 9.0, or FLAC3D 6.0/7.0/9.0.
```

### Manual Setup

**1. Register the MCP server** in your client config:

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

**2. Start the bridge from inside FLAC:**

Download [`addon.py`](addon.py), then use either of these two flows inside FLAC:

- Copy the file contents into the FLAC IPython console and run them
- Or download the file and execute it in FLAC GUI

### Verify

Restart your AI agent (Claude Code, Codex CLI, Gemini CLI, etc.). First call `flac_get_runtime_info` and confirm the reported product/dimension matches the FLAC GUI you intended to use. Then call `flac_validate_runtime` for a non-destructive bridge, command, and `.dat` file smoke test. You can also call `flac_execute_code` with:

```python
import itasca as it
print("FLAC bridge online")
print(it.command("model list information"))
```

If that works, task execution can be checked with `flac_execute_task` by passing the absolute path to a Python script that exists on the FLAC machine.

## Daily Startup

Once first-time setup is done, each new FLAC session only needs the bridge re-started — paste [`addon.py`](addon.py) into FLAC's IPython console and you're back online. The MCP client config persists.

## Features

- **Multi-version FLAC support** - command docs for FLAC 6.0, 7.0, and 9.0 via the `version` parameter
- **Versioned Python API snapshots** - FLAC3D Python API docs for 6.0, 7.0, and 9.0 are bundled
- **Product-scoped Python API docs** - Python API browse/search use FLAC2D or FLAC3D API indexes via `product` and `version`
- **FLAC2D/FLAC3D filtering** - command and reference tools accept `product` to avoid dimension-specific mismatches
- **Expanded FLAC 9.0 Python API** - bundled docs include attach, array, interface, zone, gridpoint, and vec APIs
- **Hierarchical documentation browsing** - agents navigate the FLAC command tree to discover capabilities and boundaries, reducing hallucinated commands
- **Expanded reference documentation** - plot items, boundary conditions, initial conditions, structural properties, FISH intrinsics, interfaces/joints, geometry/data/table workflows, sketch/building-block workflows, histories, and results references supplementing the official documentation
- **Legacy command availability** - FLAC3D 6.0/7.0 command coverage is resolved against official legacy command indexes; commands absent from those indexes are reported as unavailable for that version
- **Runtime validation** - one tool checks bridge connectivity, runtime identity, safe command execution, and temporary `.dat` file write/read behavior
- **Interactive REPL** - rapid iteration before committing to full scripts; agents can quickly test and refine code
- **Task lifecycle management** - submit long-running simulations, monitor progress, interrupt running tasks, and browse task history
- **Multi-client compatible** - works with Claude Code, Codex CLI, Gemini CLI, GitHub Copilot CLI, OpenCode, toyoura-nagisa, and other MCP clients

## Troubleshooting

See [Troubleshooting](docs/agentic/flac-mcp-bootstrap.md#troubleshooting) in the bootstrap guide.

## Development

See [Developer Guide: Install and Run from Source](docs/development/source-install.md).

For real FLAC software validation, use [FLAC Runtime Validation Checklist](docs/validation/flac-runtime-validation.md).

For a source checkout, clone with submodules:

```bash
git clone --recurse-submodules https://github.com/yusong652/flac-mcp.git
```

If `itasca-mcp-bridge/` is empty after cloning or pulling, run:

```bash
git submodule update --init --recursive
```

## Contributing

PRs and issues are welcome! See the [Developer Guide](docs/development/source-install.md) to get started.

## License

MIT - see [LICENSE](LICENSE).

<!-- mcp-name: io.github.yusong652/flac-mcp -->

# Developer Guide: Install and Run from Source

This guide is for contributors who want to run `flac-mcp` from a local checkout, test changes before publishing to PyPI, or install the bridge from local source into a FLAC embedded Python environment.

## Runtime Split

This repository contains two separate runtimes:

- `flac-mcp`
  The MCP server package under [`src/flac_mcp`](../../src/flac_mcp), running on standard Python `>=3.10`
- `itasca-mcp-bridge`
  The bridge package under [`itasca-mcp-bridge`](../../itasca-mcp-bridge), running inside FLAC embedded Python. This directory is a **git submodule**: its own repository ([`yusong652/itasca-mcp-bridge`](https://github.com/yusong652/itasca-mcp-bridge)) with an independent release cycle. `flac-mcp` only records *which* bridge commit to use, not the bridge's files.

Treat them as separate installation targets even though they appear in the same working tree.

## 1. Clone and Install Dev Dependencies

Clone with the bridge submodule (it is required for Steps 3–7):

```bash
git clone --recurse-submodules https://github.com/yusong652/flac-mcp.git
```

Already cloned without `--recurse-submodules`? `itasca-mcp-bridge/` is empty until you initialize it:

```bash
git submodule update --init --recursive
```

Then, from the repository root:

```bash
uv sync --group dev
```

Run tests:

```bash
uv run pytest tests
```

### Working with the bridge submodule

`itasca-mcp-bridge/` is a pinned pointer (a gitlink, mode `160000`) to one commit of the separate [`yusong652/itasca-mcp-bridge`](https://github.com/yusong652/itasca-mcp-bridge) repo — `flac-mcp` tracks a single SHA there, not the bridge's source files. Practical consequences:

- **After pulling `flac-mcp`**, re-sync the pin — the submodule working tree does not move on its own:

  ```bash
  git submodule update --init --recursive
  ```

- **To bump the bridge version**, check out the desired commit inside `itasca-mcp-bridge/`, then stage the moved pointer explicitly in `flac-mcp`:

  ```bash
  git add itasca-mcp-bridge && git commit -m "chore: bump itasca-mcp-bridge pin"
  ```

- **Push order matters**: push the bridge repo first. The pinned commit must already exist on the public bridge repo, or other clones cannot fetch it.
- `git status` showing `modified: itasca-mcp-bridge (untracked content)` usually just means the submodule working tree has local/untracked files relative to the pin — not that `flac-mcp` is tracking bridge sources. Bump the pin only when you intend to.

## 2. Point Your MCP Client at the Local Checkout

If you want your MCP client to use local source instead of the published PyPI package, point it at the repository with `uv run --directory`:

```json
{
  "mcpServers": {
    "flac-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/flac-mcp", "flac-mcp", "--bridge-url", "ws://localhost:9001"]
    }
  }
}
```

The `--bridge-url` argument is optional (defaults to `ws://localhost:9001`). To
connect to a bridge on a non-default port, pass `--bridge-port` instead of
spelling out the whole URL — e.g. `"args": [..., "flac-mcp", "--bridge-port", "9002"]`
when the bridge was started with `itasca_mcp_bridge.start(port=9002)`.

This is the simplest way to test MCP-side changes without building or publishing packages.

## 3. Run the Bridge Directly from Source

If you only need bridge-side changes to take effect in FLAC, you do not need to install the bridge package at all. In the FLAC IPython console:

```python
%run C:/path/to/flac-mcp/itasca-mcp-bridge/start_bridge.py
```

Notes:

- Use forward slashes in the path.
- Do not wrap the `%run` path in quotes.
- Restart the bridge after source changes.

This is the fastest workflow for bridge development.

## 4. Install the Bridge from Local Source into Embedded Python

If you want to test the package installation path itself, install `itasca-mcp-bridge` from local source using the embedded Python interpreter from a terminal.

Pick the correct interpreter for your FLAC version:

- FLAC `6.0` / `7.0`: `C:/Program Files/Itasca/.../exe64/python36/python.exe`
- FLAC `9.0`: `C:/Program Files/Itasca/.../exe64/python310/python.exe`

Example commands:

```powershell
& "C:\Program Files\Itasca\FLAC700\exe64\python36\python.exe" -m pip install --user -e C:\path\to\flac-mcp\itasca-mcp-bridge
& "C:\Program Files\Itasca\ItascaSoftware900\exe64\python310\python.exe" -m pip install --user -e C:\path\to\flac-mcp\itasca-mcp-bridge
```

Why use the embedded interpreter from a terminal:

- It installs into the exact Python environment used by FLAC.
- It avoids relying on `subprocess` calls from inside the FLAC console.
- It is the most reliable workflow for editable installs.

The bridge package will pull a matching `websockets` version automatically:

- Python `3.6` -> `websockets==9.1`
- Python `3.10` -> `websockets==16.0`

## 5. Install from Inside FLAC IPython

For PyPI-based installation inside the FLAC console, use the version-aware snippet from the main README:

- FLAC `6.0` / `7.0`: `pip.main(...)`
- FLAC `9.0`: `pip._internal.cli.main.main(...)`

For source installs, prefer the terminal-based embedded-interpreter workflow from Step 4 instead of trying to drive an editable install from inside the FLAC GUI console.

## 6. Verify the Environment

Verify the bridge package inside embedded Python:

```powershell
& "C:\Program Files\Itasca\ItascaSoftware900\exe64\python310\python.exe" -c "import itasca_mcp_bridge, websockets; print(itasca_mcp_bridge.__version__); print(websockets.__version__)"
```

Then start the bridge in FLAC and verify from your MCP client:

1. Start the bridge in FLAC with `itasca_mcp_bridge.start()` or `%run .../start_bridge.py`
2. Restart the MCP client session
3. Call `flac_list_tasks`

## 7. Recommended Dev Loop

For most day-to-day work:

1. Run `uv sync --group dev`
2. Point your MCP client at the local checkout with `uv run --directory`
3. Use `%run .../itasca-mcp-bridge/start_bridge.py` inside FLAC
4. Run `uv run pytest tests`
5. Restart the MCP client and bridge after changes when needed

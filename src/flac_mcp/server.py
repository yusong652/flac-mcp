"""FLAC MCP Server - ITASCA FLAC3D tools exposed over MCP."""

import argparse
import asyncio
import logging
import os
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from fastmcp import FastMCP

from flac_mcp import __version__
from flac_mcp.bridge import close_bridge_client
from flac_mcp.tools import (
    browse_commands,
    browse_python_api,
    browse_reference,
    check_task_status,
    execute_code,
    execute_task,
    interrupt_task,
    list_tasks,
    query_command,
    query_python_api,
)

mcp = FastMCP(
    "FLAC MCP Server",
    instructions=(
        "⚠️ DEPRECATED: the 'flac-mcp' package is superseded by 'itasca-mcp', "
        "a single multi-engine server covering FLAC, PFC, 3DEC, MPoint, and "
        "MassFlow. This package is frozen and receives no further updates. "
        "Please update your MCP client config from `uvx flac-mcp` to "
        "`uvx itasca-mcp` (FLAC3D docs are selected with the `software` "
        "parameter). The tools below still work against an itasca-mcp-bridge.\n\n"
        "FLAC3D MCP server. "
        "Provides tools for browsing/searching ITASCA reference documentation "
        "and for executing simulation tasks and managing runs "
        "through an itasca-mcp-bridge HTTP service running inside FLAC3D."
    ),
)

logger = logging.getLogger("flac-mcp.server")

# Register documentation tools
browse_commands.register(mcp)
browse_python_api.register(mcp)
browse_reference.register(mcp)
query_command.register(mcp)
query_python_api.register(mcp)

# Register execution tools
execute_task.register(mcp)
check_task_status.register(mcp)
list_tasks.register(mcp)
interrupt_task.register(mcp)
execute_code.register(mcp)


DEFAULT_BRIDGE_URL = "http://localhost:9001"


def _override_bridge_port(url: str, port: int) -> str:
    """Return ``url`` with its port replaced, preserving scheme/host/path."""
    parts = urlsplit(url)
    host = parts.hostname or "localhost"
    return urlunsplit((parts.scheme or "http", f"{host}:{port}", parts.path, parts.query, parts.fragment))


def main() -> None:
    """Entry point for the FLAC MCP server."""
    parser = argparse.ArgumentParser(
        prog="flac-mcp",
        description="FLAC MCP Server - ITASCA FLAC3D tools exposed over MCP",
    )
    parser.add_argument("--version", "-v", action="version", version=f"flac-mcp {__version__}")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind when using http/sse transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind when using http/sse transport (default: 8000)",
    )
    parser.add_argument(
        "--bridge-url",
        default=None,
        help="Bridge HTTP URL (default: http://localhost:9001, or FLAC_MCP_BRIDGE_URL env)",
    )
    parser.add_argument(
        "--bridge-port",
        type=int,
        default=None,
        help=(
            "Bridge HTTP port; shorthand for --bridge-url http://localhost:PORT. "
            "Overrides only the port of --bridge-url / FLAC_MCP_BRIDGE_URL when both "
            "are given (default: 9001)"
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="warning",
        help="Log level for flac-mcp (default: warning)",
    )
    args = parser.parse_args()

    # Resolve the bridge URL from (in order of precedence) --bridge-url,
    # the FLAC_MCP_BRIDGE_URL env, then the default. --bridge-port then
    # overrides just the port, so users can point at a non-default bridge
    # port without spelling out the whole http:// URL.
    bridge_url = args.bridge_url or os.environ.get("FLAC_MCP_BRIDGE_URL")
    if args.bridge_port is not None:
        if not 1 <= args.bridge_port <= 65535:
            parser.error("--bridge-port must be between 1 and 65535")
        bridge_url = _override_bridge_port(bridge_url or DEFAULT_BRIDGE_URL, args.bridge_port)
    if bridge_url:
        os.environ["FLAC_MCP_BRIDGE_URL"] = bridge_url

    # Configure logging
    level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("flac-mcp").setLevel(level)
    # Keep uvicorn quiet unless user asks for debug/info
    uvicorn_level = level if level <= logging.INFO else logging.CRITICAL
    logging.getLogger("uvicorn").setLevel(uvicorn_level)
    logging.getLogger("uvicorn.error").setLevel(uvicorn_level)

    run_kwargs: dict[str, Any] = {"transport": args.transport, "show_banner": False}
    if args.transport in ("http", "sse"):
        run_kwargs["host"] = args.host
        run_kwargs["port"] = args.port

    try:
        mcp.run(**run_kwargs)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            asyncio.run(close_bridge_client())
        except Exception as exc:
            logger.debug("Bridge client cleanup skipped: %s", exc)


if __name__ == "__main__":
    main()

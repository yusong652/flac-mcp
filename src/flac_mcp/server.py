"""FLAC MCP Server - ITASCA FLAC tools exposed over MCP."""

import argparse
import asyncio
import logging
import os
from typing import Any

from fastmcp import FastMCP

from flac_mcp import __version__
from flac_mcp.bridge import close_bridge_client
from flac_mcp.tools import (
    browse_commands,
    browse_python_api,
    browse_reference,
    check_task_status,
    command_coverage,
    execute_code,
    execute_task,
    interrupt_task,
    list_tasks,
    python_api_coverage,
    query_command,
    query_python_api,
    runtime_info,
)

mcp = FastMCP(
    "FLAC MCP Server",
    instructions=(
        "FLAC MCP server for FLAC2D/FLAC3D workflows. "
        "Provides tools for browsing/searching ITASCA reference documentation "
        "and for executing simulation tasks and managing runs "
        "through an itasca-mcp-bridge WebSocket service running inside FLAC."
    ),
)

logger = logging.getLogger("flac-mcp.server")

# Register documentation tools
browse_commands.register(mcp)
browse_python_api.register(mcp)
browse_reference.register(mcp)
query_command.register(mcp)
query_python_api.register(mcp)
command_coverage.register(mcp)
python_api_coverage.register(mcp)

# Register execution tools
execute_task.register(mcp)
check_task_status.register(mcp)
list_tasks.register(mcp)
interrupt_task.register(mcp)
execute_code.register(mcp)
runtime_info.register(mcp)


def main() -> None:
    """Entry point for the FLAC MCP server."""
    parser = argparse.ArgumentParser(
        prog="flac-mcp",
        description="FLAC MCP Server - ITASCA FLAC tools exposed over MCP",
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
        help="Bridge WebSocket URL (default: ws://localhost:9002, or FLAC_MCP_BRIDGE_URL env)",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="warning",
        help="Log level for flac-mcp (default: warning)",
    )
    args = parser.parse_args()

    if args.bridge_url:
        os.environ["FLAC_MCP_BRIDGE_URL"] = args.bridge_url

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

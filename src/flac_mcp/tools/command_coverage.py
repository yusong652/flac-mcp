"""FLAC command documentation coverage report tool."""

from typing import Any

from fastmcp import FastMCP

from flac_mcp.contracts import build_ok
from flac_mcp.knowledge.commands.coverage import build_command_coverage


def register(mcp: FastMCP) -> None:
    """Register flac_command_coverage tool."""

    @mcp.tool()
    def flac_command_coverage() -> dict[str, Any]:
        """Report bundled command coverage for applicable FLAC2D/FLAC3D versions.

        This is a documentation-audit tool. It does not require a running
        bridge. Use it before relying on command browse/search results for
        version- or dimension-specific work.
        """
        return build_ok(build_command_coverage())

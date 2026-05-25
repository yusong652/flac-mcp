"""FLAC Python API documentation coverage report tool."""

from typing import Any

from fastmcp import FastMCP

from flac_mcp.contracts import build_ok
from flac_mcp.knowledge.python_api.coverage import build_python_api_coverage


def register(mcp: FastMCP) -> None:
    """Register flac_python_api_coverage tool."""

    @mcp.tool()
    def flac_python_api_coverage() -> dict[str, Any]:
        """Report bundled Python API coverage for FLAC2D/FLAC3D and 6.0/7.0/9.0.

        This is a documentation-audit tool. It does not require a running
        bridge. Use it before relying on Python API browse/search results for
        version- or dimension-specific work.
        """
        return build_ok(build_python_api_coverage())

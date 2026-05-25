"""High-level query interfaces for FLAC documentation search.

This module provides user-facing search APIs that abstract away
the complexity of search engines and adapters.
"""

from flac_mcp.knowledge.query.api_search import APISearch
from flac_mcp.knowledge.query.command_search import CommandSearch

__all__ = [
    "CommandSearch",
    "APISearch",
]

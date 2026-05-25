"""Search infrastructure for FLAC documentation systems.

Provides unified search components used by both command search
and Python API search systems.
"""

from flac_mcp.knowledge.search.base import SearchStrategy
from flac_mcp.knowledge.search.legacy_models import (
    CommandSearchResult,  # Backward compatibility alias
    DocumentType,
    SearchResult,
)
from flac_mcp.knowledge.search.legacy_models import SearchStrategy as SearchStrategyEnum

__all__ = [
    "SearchStrategy",
    "SearchResult",
    "DocumentType",
    "SearchStrategyEnum",
    "CommandSearchResult",
]

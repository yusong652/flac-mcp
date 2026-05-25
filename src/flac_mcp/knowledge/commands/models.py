"""Data models for FLAC command documentation system.

DEPRECATED: This module is kept for backward compatibility only.
New code should use flac_mcp.knowledge.search.legacy_models instead.
"""

# Import from unified models for backward compatibility
from flac_mcp.knowledge.search.legacy_models import DocumentType, SearchStrategy
from flac_mcp.knowledge.search.legacy_models import SearchResult as CommandSearchResult

# Re-export for backward compatibility
__all__ = ["CommandSearchResult", "DocumentType", "SearchStrategy"]

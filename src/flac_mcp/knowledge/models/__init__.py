"""Shared models for FLAC search system.

This package provides unified data models for the search infrastructure,
enabling consistent handling of different document types (commands, APIs, etc.).
"""

from flac_mcp.knowledge.models.document import DocumentType, SearchDocument
from flac_mcp.knowledge.models.search_result import SearchResult

__all__ = ["DocumentType", "SearchDocument", "SearchResult"]

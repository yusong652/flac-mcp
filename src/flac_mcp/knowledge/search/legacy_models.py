"""Unified search result models for FLAC documentation systems.

This module provides shared data structures for search results across
command and Python API documentation systems.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DocumentType(Enum):
    """Type of documentation being searched.

    This enum unifies document types across all FLAC documentation systems:
    - COMMAND: FLAC commands (e.g., "zone create", "zone property")
    - MODEL_PROPERTY: Contact model properties (e.g., "linear", "rrlinear")
    - API: Python SDK APIs (e.g., "itasca.zone.create", "Zone.pos")
    """

    COMMAND = "command"
    MODEL_PROPERTY = "model_property"
    API = "api"


class SearchStrategy(Enum):
    """Search strategy used to find the result.

    Represents which search strategy was used:
    - PATH: Exact path matching (e.g., "itasca.zone.create")
    - KEYWORD: Keyword-based matching (multi-word, partial matching)
    - SEMANTIC: Future embedding-based semantic search
    """

    PATH = "path"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"


@dataclass
class SearchResult:
    """Unified search result across all FLAC documentation types.

    This model replaces both CommandSearchResult and the Python API SearchResult,
    providing a single unified interface for all search operations.

    Attributes:
        name: Item name (command name, model name, or API path)
        score: Relevance score (higher = more relevant, typically 0-1000)
        doc_type: Type of documentation (COMMAND, MODEL_PROPERTY, or API)
        category: Category/module name (e.g., "zone", "linear", "zone")
        strategy: Search strategy used (PATH, KEYWORD, or SEMANTIC)
        metadata: Type-specific additional data (optional)

    Examples:
        Command result:
            SearchResult(
                name="zone create",
                score=1000,
                doc_type=DocumentType.COMMAND,
                category="zone",
                strategy=SearchStrategy.KEYWORD,
                metadata={
                    "file": "commands/zone/create.json",
                    "short_description": "Create a single zone",
                    "syntax": "zone create <keyword> ...",
                    "python_available": True
                }
            )

        Model property result:
            SearchResult(
                name="linear",
                score=950,
                doc_type=DocumentType.MODEL_PROPERTY,
                category="linear",
                strategy=SearchStrategy.KEYWORD,
                metadata={
                    "file": "model-properties/linear.json",
                    "full_name": "Linear Model",
                    "description": "Linear elastic-frictional zone model...",
                    "priority": "high"
                }
            )

        Python API result (exact path):
            SearchResult(
                name="itasca.zone.create",
                score=999,
                doc_type=DocumentType.API,
                category="zone",
                strategy=SearchStrategy.PATH,
                metadata=None
            )

        Python API result (Contact type with grouping):
            SearchResult(
                name="itasca.ZoneZoneContact.gap",
                score=1070,
                doc_type=DocumentType.API,
                category="zone",
                strategy=SearchStrategy.KEYWORD,
                metadata={
                    "all_zone_types": ["ZoneZoneContact", "ZoneFacetContact", ...],
                    "zone_method": "gap"
                }
            )
    """

    name: str
    score: int
    doc_type: DocumentType
    category: str
    strategy: SearchStrategy
    metadata: dict[str, Any] | None = None


# Backward compatibility aliases
# These allow existing code to continue using old names while we migrate
CommandSearchResult = SearchResult  # For command system
# Note: Python API already uses "SearchResult", so no alias needed there

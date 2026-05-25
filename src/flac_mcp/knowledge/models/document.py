"""Unified document model for FLAC search system.

This module provides a unified representation of different document types
(commands, model properties, Python API) to enable consistent search operations
across the entire FLAC documentation system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DocumentType(Enum):
    """Document type enumeration.

    Defines the types of searchable documents in the FLAC system:
    - COMMAND: FLAC command documentation (e.g., "zone create", "zone property")
    - MODEL_PROPERTY: Constitutive model property documentation (e.g., "mohr-coulomb", "elastic")
    - PYTHON_API: Python SDK API documentation (e.g., "itasca.zone.create")

    Search Strategy:
    - COMMAND + MODEL_PROPERTY: Unified search via CommandSearch
    - PYTHON_API: Independent search via APISearch
    """

    COMMAND = "command"
    MODEL_PROPERTY = "model_property"
    PYTHON_API = "python_api"


@dataclass
class SearchDocument:
    """Unified search document model.

    This class provides a common interface for all searchable documents,
    abstracting away differences between commands, APIs, and model properties.

    Design Goals:
    - Unified search: Same search algorithms work for all document types
    - Extensible: Easy to add new document types via metadata
    - Type-safe: Explicit typing prevents errors

    Attributes:
        name: Unique document name/identifier
            Examples:
            - COMMAND: "zone create", "zone property"
            - MODEL_PROPERTY: "mohr-coulomb", "elastic"
            - PYTHON_API: "itasca.zone.create", "Zone.vel"
        doc_type: Type of document (COMMAND/MODEL_PROPERTY/PYTHON_API)
        title: Display title for search results
        description: Full text description for BM25 search
        keywords: Human-curated search keywords for exact/partial matching
        category: Document category for filtering
            Examples: "zone" (commands), "constitutive-models" (model), "itasca.zone" (API)
        syntax: Command/function syntax for display
        examples: Usage examples list
        metadata: Extensible metadata dictionary for custom fields
            Common fields:
            - python_available (bool): Python SDK alternative exists
            - file_path (str): Source JSON file path
            - priority (str): "high", "medium", "low" for ranking
            - property_count (int): Number of properties (model docs)

    Usage:
        >>> # Command document
        >>> cmd_doc = SearchDocument(
        ...     name="zone create",
        ...     doc_type=DocumentType.COMMAND,
        ...     title="zone create",
        ...     description="Create a new zone object...",
        ...     keywords=["create", "zone", "generate"],
        ...     category="zone",
        ...     syntax="zone create <keyword> ..."
        ... )

        >>> # Model property document
        >>> model_doc = SearchDocument(
        ...     name="linear",
        ...     doc_type=DocumentType.MODEL_PROPERTY,
        ...     title="Mohr-Coulomb Model",
        ...     description="Mohr-Coulomb zone constitutive model...",
        ...     keywords=["mohr-coulomb", "zone model", "cohesion"],
        ...     category="constitutive-models",
        ...     metadata={"priority": "high", "property_count": 8}
        ... )
    """

    # Required fields
    name: str
    doc_type: DocumentType
    title: str
    description: str
    keywords: list[str]

    # Optional fields (with defaults)
    category: str | None = None
    syntax: str | None = None
    examples: list[dict[str, str]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize fields after initialization."""
        # Ensure metadata is initialized
        if self.metadata is None:
            self.metadata = {}

        # Ensure examples is initialized
        if self.examples is None:
            self.examples = []

        # Normalize keywords (lowercase for consistent matching)
        self.keywords = [k.lower() for k in self.keywords]

    def matches_filters(self, filters: dict[str, Any]) -> bool:
        """Check if document matches filter criteria.

        Args:
            filters: Dictionary of filter conditions
                Supported keys:
                - category: Filter by category (e.g., "zone", "constitutive-models")
                - doc_type: Filter by document type
                - Any metadata key: Filter by metadata values

        Returns:
            True if document matches all filters, False otherwise

        Example:
            >>> doc.matches_filters({"category": "zone"})
            True
            >>> doc.matches_filters({"doc_type": DocumentType.MODEL_PROPERTY})
            False
            >>> doc.matches_filters({"metadata.priority": "high"})
            True
        """
        for key, value in filters.items():
            if key == "category" and self.category != value:
                return False
            if key == "doc_type" and self.doc_type != value:
                return False
            # Check metadata (support nested keys like "metadata.priority")
            if key.startswith("metadata."):
                meta_key = key.replace("metadata.", "")
                if self.metadata.get(meta_key) != value:
                    return False
            # Direct metadata check
            elif key in self.metadata and self.metadata[key] != value:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert document to dictionary representation.

        Useful for serialization, logging, and API responses.

        Returns:
            Dictionary with all document fields
        """
        return {
            "name": self.name,
            "doc_type": self.doc_type.value,
            "title": self.title,
            "description": self.description,
            "keywords": self.keywords,
            "category": self.category,
            "syntax": self.syntax,
            "examples": self.examples,
            "metadata": self.metadata,
        }

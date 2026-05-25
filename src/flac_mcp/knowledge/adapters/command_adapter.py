"""Command document adapter for FLAC search system.

This module converts FLAC command documentation from the CommandLoader format
into unified SearchDocument models for search.

Note: Model properties are handled separately via flac_browse_reference tool.
"""

from flac_mcp.knowledge.commands.loader import CommandLoader
from flac_mcp.knowledge.models import DocumentType, SearchDocument


class CommandDocumentAdapter:
    """Adapter for FLAC command documentation.

    Converts command data from CommandLoader into unified SearchDocument format.
    This enables:
    - Consistent interface for search engines
    - Separation of data loading and search logic

    Note: For zone model properties, use flac_browse_reference tool directly.

    Usage:
        >>> documents = CommandDocumentAdapter.load_commands()
        >>> len(documents)
        115  # 115 commands across 7 categories
    """

    @staticmethod
    def load_commands(version: str = CommandLoader.DEFAULT_VERSION) -> list[SearchDocument]:
        """Load all FLAC command documents.

        Returns:
            List of SearchDocument instances for all commands

        Example:
            >>> docs = CommandDocumentAdapter.load_commands()
            >>> doc = docs[0]
            >>> doc.name
            'zone create'
            >>> doc.doc_type
            <DocumentType.COMMAND: 'command'>
        """
        documents = []
        all_commands = CommandLoader.get_all_commands()

        for cmd_meta in all_commands:
            category = cmd_meta["category"]
            cmd_name = cmd_meta["name"]

            # Load full command documentation. A KeyError means the doc has
            # no entry for this version (e.g. FLAC 9.0-only docs when the
            # 7.0 engine is built, or any doc lacking the requested 6.0).
            # That doc is legitimately absent from this version's index —
            # skip it rather than crash the whole index build.
            try:
                cmd_doc = CommandLoader.load_command_doc(category, cmd_name, version)
            except KeyError:
                continue
            if not cmd_doc or cmd_doc.get("available") is False:
                continue

            # Convert to SearchDocument
            doc = SearchDocument(
                name=f"{category} {cmd_name}",
                doc_type=DocumentType.COMMAND,
                title=cmd_doc.get("command", f"{category} {cmd_name}"),
                description=cmd_doc.get("description", ""),
                keywords=cmd_doc.get("search_keywords", []),
                category=category,
                syntax=cmd_doc.get("syntax"),
                examples=cmd_doc.get("examples", []),
                metadata={
                    "python_available": cmd_doc.get("python_sdk_alternative", {}).get("available", False),
                    "file": cmd_meta.get("file"),
                    "short_description": cmd_meta.get("short_description", ""),
                    "version": version,
                },
            )
            documents.append(doc)

        return documents

    # Alias for backward compatibility
    load_all = load_commands

    @staticmethod
    def load_by_id(doc_id: str, version: str = CommandLoader.DEFAULT_VERSION) -> SearchDocument | None:
        """Load a specific command document by ID.

        Args:
            doc_id: Document ID in "category command" format (e.g., "zone create")

        Returns:
            SearchDocument instance or None if not found

        Example:
            >>> doc = CommandDocumentAdapter.load_by_id("zone create")
            >>> doc.title
            'zone create'
        """
        if " " not in doc_id:
            return None

        category, cmd_name = doc_id.split(" ", 1)
        try:
            cmd_doc = CommandLoader.load_command_doc(category, cmd_name, version)
        except KeyError:
            return None

        if not cmd_doc or cmd_doc.get("available") is False:
            return None

        return SearchDocument(
            name=doc_id,
            doc_type=DocumentType.COMMAND,
            title=cmd_doc.get("command", doc_id),
            description=cmd_doc.get("description", ""),
            keywords=cmd_doc.get("search_keywords", []),
            category=category,
            syntax=cmd_doc.get("syntax"),
            examples=cmd_doc.get("examples", []),
            metadata={
                "python_available": cmd_doc.get("python_sdk_alternative", {}).get("available", False),
                "version": version,
            },
        )

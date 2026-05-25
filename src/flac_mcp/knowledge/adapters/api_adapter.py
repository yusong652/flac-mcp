"""Python API document adapter for FLAC search."""

from flac_mcp.knowledge.models.document import DocumentType, SearchDocument
from flac_mcp.knowledge.python_api.loader import DocumentationLoader
from flac_mcp.knowledge.python_api.types.mappings import CLASS_TO_MODULE


class APIDocumentAdapter:
    """Convert Python SDK API docs into unified search documents."""

    @staticmethod
    def load_all() -> list[SearchDocument]:
        """Load all function and method API documents."""
        documents = []
        index = DocumentationLoader.load_index()
        quick_ref = index.get("quick_ref", {})
        all_keywords = DocumentationLoader.load_all_keywords()

        for api_name, file_ref in quick_ref.items():
            api_doc = DocumentationLoader.load_api_doc(api_name)
            if not api_doc or api_doc.get("type") == "module":
                continue

            description = api_doc.get("description", "")
            parameters = api_doc.get("parameters", [])
            if parameters:
                description += "\n\nParameters: " + ", ".join(p.get("name", "") for p in parameters)

            keywords = [keyword for keyword, api_list in all_keywords.items() if api_name in api_list]
            documents.append(
                SearchDocument(
                    name=api_name,
                    doc_type=DocumentType.PYTHON_API,
                    title=api_name,
                    description=description,
                    keywords=keywords,
                    category=APIDocumentAdapter._extract_category(api_name),
                    syntax=api_doc.get("signature", api_name),
                    examples=[{"code": ex} if isinstance(ex, str) else ex for ex in api_doc.get("examples", [])],
                    metadata={
                        "file_ref": file_ref,
                        "returns": api_doc.get("returns", ""),
                        "limitations": api_doc.get("limitations", []),
                        "fallback_commands": api_doc.get("fallback_commands", []),
                        "see_also": api_doc.get("see_also", []),
                    },
                )
            )

        return documents

    @staticmethod
    def _extract_category(api_name: str) -> str:
        """Extract category from an API name."""
        parts = api_name.split(".")
        if api_name.startswith("itasca.") and len(parts) >= 3:
            return ".".join(parts[:2])
        if len(parts) == 2 and parts[0] in CLASS_TO_MODULE:
            return f"itasca.{CLASS_TO_MODULE[parts[0]]}"
        if len(parts) >= 2:
            return ".".join(parts[:2])
        return parts[0] if parts else "unknown"

    @staticmethod
    def load_by_id(doc_id: str) -> SearchDocument | None:
        """Load a specific API document by ID."""
        api_doc = DocumentationLoader.load_api_doc(doc_id)
        if not api_doc or api_doc.get("type") == "module":
            return None

        description = api_doc.get("description", "")
        parameters = api_doc.get("parameters", [])
        if parameters:
            description += "\n\nParameters: " + ", ".join(p.get("name", "") for p in parameters)

        keywords = [
            keyword for keyword, api_list in DocumentationLoader.load_all_keywords().items() if doc_id in api_list
        ]
        return SearchDocument(
            name=doc_id,
            doc_type=DocumentType.PYTHON_API,
            title=doc_id,
            description=description,
            keywords=keywords,
            category=APIDocumentAdapter._extract_category(doc_id),
            syntax=api_doc.get("signature", doc_id),
            examples=[{"code": ex} if isinstance(ex, str) else ex for ex in api_doc.get("examples", [])],
            metadata={
                "returns": api_doc.get("returns", ""),
                "limitations": api_doc.get("limitations", []),
                "see_also": api_doc.get("see_also", []),
            },
        )

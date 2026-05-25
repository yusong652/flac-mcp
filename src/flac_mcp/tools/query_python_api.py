"""FLAC Python API Query Tool - Keyword search for SDK documentation."""

from typing import Any

from fastmcp import FastMCP

from flac_mcp.contracts import build_docs_data, build_ok
from flac_mcp.knowledge.python_api import APIDocFormatter, DocumentationLoader
from flac_mcp.knowledge.query import APISearch
from flac_mcp.utils import PythonAPISearchQuery, SearchLimit


def register(mcp: FastMCP) -> None:
    """Register flac_query_python_api tool with the MCP server."""

    @mcp.tool()
    def flac_query_python_api(
        query: PythonAPISearchQuery,
        limit: SearchLimit = 10,
    ) -> dict[str, Any]:
        """Search FLAC Python SDK documentation by keywords (like grep).

        Returns matching API paths with signatures. Use flac_browse_python_api for full documentation.

        When to use:
        - You have keywords but don't know exact API path
        - Example: "zone stress", "gridpoint displacement", "create"

        Related tools:
        - flac_browse_python_api: Get full documentation for a known API path
        - flac_query_command: Search FLAC commands by keywords
        """
        matches = APISearch.search(query, top_k=limit)
        results_payload: list[dict[str, Any]] = []
        for result in matches:
            api_path = result.document.name
            sig = APIDocFormatter.format_signature(api_path, result.document.metadata)
            results_payload.append(
                {
                    "api_path": api_path,
                    "signature": sig,
                    "category": result.document.category,
                    "description": result.document.description,
                    "score": round(result.score, 2),
                    "rank": result.rank,
                    "metadata": result.document.metadata,
                }
            )

        payload: dict[str, Any] = build_docs_data(
            source="python_api",
            action="query",
            entries=results_payload,
            summary={
                "count": len(results_payload),
            },
        )

        if not results_payload:
            index = DocumentationLoader.load_index()
            hints = []
            for hint_key, hint_msg in index.get("fallback_hints", {}).items():
                if hint_key in query.lower():
                    hints.append(hint_msg)
            if hints:
                payload["summary"]["hints"] = hints

        return build_ok(payload)

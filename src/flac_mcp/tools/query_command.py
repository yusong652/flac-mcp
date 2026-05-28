"""FLAC Command Query Tool - Keyword search for command documentation."""

from typing import Any

from fastmcp import FastMCP
from pydantic import Field

from flac_mcp.contracts import build_docs_data, build_ok
from flac_mcp.knowledge.commands import CommandLoader
from flac_mcp.knowledge.query import CommandSearch
from flac_mcp.utils import CommandDocVersion, SearchLimit, SearchQuery, normalize_command_doc_version


def register(mcp: FastMCP) -> None:
    """Register flac_query_command tool with the MCP server."""

    @mcp.tool()
    def flac_query_command(
        query: SearchQuery,
        limit: SearchLimit = 10,
        version: CommandDocVersion = Field(
            CommandDocVersion.V9_0,
            description=(
                "FLAC documentation version to search. Defaults to 9.0 "
                "(current ITASCA Software release; covers FLAC continuum + "
                "structural-element commands)."
            ),
        ),
    ) -> dict[str, Any]:
        """Search FLAC command documentation by keywords (like grep).

        Returns matching command paths. Use flac_browse_commands for full documentation.

        When to use:
        - You have keywords but don't know exact command path
        - Example: "zone create", "structure cable", "model solve"

        Related tools:
        - flac_browse_commands: Get full documentation for a known command path
        - flac_browse_reference: Browse reference docs (e.g., "constitutive-models mohr-coulomb")
        - flac_query_python_api: Search Python SDK by keywords
        """
        version_value = normalize_command_doc_version(version)
        results = CommandSearch.search_commands_only(query, top_k=limit, version=version_value)
        matches: list[dict[str, Any]] = []
        for result in results:
            metadata = result.document.metadata or {}
            matches.append(
                {
                    "path": result.document.title,
                    "name": result.document.name,
                    "category": result.document.category,
                    "syntax": result.document.syntax,
                    "short_description": metadata.get("short_description"),
                    "score": round(result.score, 2),
                    "rank": result.rank,
                    "version": metadata.get("version", version_value),
                }
            )

        payload: dict[str, Any] = build_docs_data(
            source="commands",
            action="query",
            entries=matches,
            summary={
                "count": len(matches),
                "version": version_value,
            },
        )

        if not matches:
            categories = sorted(CommandLoader.load_index().get("categories", {}).keys())
            payload["summary"]["hints"] = [
                "Try broader keywords (for example: create, property, solve).",
                "Try category + action (for example: zone create, structure cable, model solve).",
            ]
            payload["summary"]["available_categories"] = categories

        return build_ok(payload)

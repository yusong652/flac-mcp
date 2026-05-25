"""High-level Python API search interface."""

from typing import Any

from flac_mcp.knowledge.adapters.api_adapter import APIDocumentAdapter
from flac_mcp.knowledge.models.search_result import SearchResult
from flac_mcp.knowledge.search.engines.bm25_engine import BM25SearchEngine
from flac_mcp.knowledge.search.postprocessing import consolidate_component_apis


class APISearch:
    """Search FLAC Python SDK APIs using BM25 with component consolidation."""

    @classmethod
    def search(
        cls,
        query: str,
        top_k: int = 10,
        category: str | None = None,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Search for Python SDK APIs.

        Examples:
        - Natural language: ``zone stress``, ``gridpoint displacement``
        - API paths: ``Zone.stress``, ``Gridpoint.pos``
        - Category filters: ``zone``, ``gridpoint``
        """
        engine = BM25SearchEngine(document_loader=APIDocumentAdapter.load_all)
        engine.build()

        filters: dict[str, Any] = {}
        if category is not None:
            filters["category"] = category
        filters["min_score"] = 1.0 if min_score is None else min_score

        search_limit = min(top_k * 4, 100)
        results = engine.search(query=query, top_k=search_limit, filters=filters if filters else None)
        consolidated = consolidate_component_apis(results)
        return consolidated[:top_k]

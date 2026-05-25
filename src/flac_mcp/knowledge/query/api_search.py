"""High-level Python API search interface."""

import re
from typing import Any

from flac_mcp.knowledge.adapters.api_adapter import APIDocumentAdapter
from flac_mcp.knowledge.compatibility import FLACProduct
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
        product: str | FLACProduct | None = FLACProduct.ANY.value,
        version: str | None = "9.0",
    ) -> list[SearchResult]:
        """Search for Python SDK APIs.

        Examples:
        - Natural language: ``zone stress``, ``gridpoint displacement``
        - API paths: ``Zone.stress``, ``Gridpoint.pos``
        - Category filters: ``zone``, ``gridpoint``
        """
        engine = BM25SearchEngine(document_loader=lambda: APIDocumentAdapter.load_all(product, version))
        engine.build()

        filters: dict[str, Any] = {}
        if category is not None:
            filters["category"] = category
        filters["min_score"] = 1.0 if min_score is None else min_score

        search_limit = min(top_k * 4, 100)
        results = engine.search(query=query, top_k=search_limit, filters=filters if filters else None)
        if re.search(r"_[xyz]\b", query, flags=re.IGNORECASE):
            return results[:top_k]

        consolidated = consolidate_component_apis(results)
        return consolidated[:top_k]

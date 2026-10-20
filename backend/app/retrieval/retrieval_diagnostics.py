from __future__ import annotations

from typing import Any, Dict, List


def build_diagnostics(**kwargs: Any) -> Dict[str, Any]:
    return {
        "bm25_count": kwargs.get("bm25_count", 0),
        "vector_count": kwargs.get("vector_count", 0),
        "fused_count": kwargs.get("fused_count", 0),
        "applied_filters": kwargs.get("applied_filters", {}),
        "rejected_results": kwargs.get("rejected_results", []),
        "duration_ms": kwargs.get("duration_ms", 0.0),
        "rerank_enabled": kwargs.get("rerank_enabled", False),
        "reranked_count": kwargs.get("reranked_count", 0),
        "missing_tax_year_metadata": kwargs.get("missing_tax_year_metadata", []),
    }

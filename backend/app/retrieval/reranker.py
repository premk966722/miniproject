from __future__ import annotations

from typing import Any, Dict, List, Optional


class Reranker:
    def __init__(self, enabled: bool = False, model_name: Optional[str] = None):
        self.enabled = enabled
        self.model_name = model_name
        self.model = None

    def rerank(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        if not self.enabled or not results:
            return results
        reranked = []
        for result in results:
            score = float(result.get("score", 0.0))
            if query.lower() in (result.get("text") or "").lower():
                score += 0.25
            enriched = dict(result)
            enriched["reranker_score"] = score
            reranked.append(enriched)
        reranked.sort(key=lambda item: item["reranker_score"], reverse=True)
        return reranked

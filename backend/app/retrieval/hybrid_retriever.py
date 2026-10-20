from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.metadata_filter import filter_hits_by_metadata
from app.retrieval.query_analyzer import analyze_query
from app.retrieval.reranker import Reranker
from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.vector_retriever import VectorRetriever


class HybridRetriever:
    def __init__(self, documents: Optional[List[Dict[str, Any]]] = None) -> None:
        self.documents = documents or []
        self.bm25 = BM25Retriever()
        self.vector = VectorRetriever()
        self.reranker = Reranker(enabled=False)
        self._index_documents()

    def _index_documents(self) -> None:
        self.bm25.index_documents(self.documents)
        self.vector.index_documents(self.documents)

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = documents
        self._index_documents()

    def _normalize_result(self, hit: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(hit)
        normalized.setdefault("title", hit.get("document_title") or hit.get("title") or "Untitled")
        normalized.setdefault("url", hit.get("source_url") or hit.get("url"))
        normalized.setdefault("authority", hit.get("issuing_authority") or hit.get("authority") or "Unknown")
        normalized.setdefault("source_type", hit.get("document_type") or hit.get("source_type"))
        normalized.setdefault("document_title", normalized["title"])
        normalized.setdefault("source_url", normalized["url"])
        normalized.setdefault("issuing_authority", normalized["authority"])
        normalized.setdefault("metadata", hit.get("metadata") or hit)
        return normalized

    def search(
        self,
        query: str,
        tax_year: Optional[str] = None,
        assessment_year: Optional[str] = None,
        section_number: Optional[str] = None,
        top_k: int = 5,
        bm25_top_k: int = 10,
        vector_top_k: int = 10,
        rerank: bool = False,
    ) -> List[Dict[str, Any]]:
        if not self.documents:
            return []

        started = time.time()
        analysis = analyze_query(query)
        if section_number is None:
            section_number = analysis.get("section_number")
        if tax_year is None:
            tax_year = analysis.get("tax_year")
        if assessment_year is None:
            assessment_year = analysis.get("assessment_year")
        period_filter = assessment_year or tax_year

        bm25_hits = self.bm25.search(query, top_k=bm25_top_k, tax_year=period_filter, section_number=section_number)
        vector_hits = self.vector.search(query, top_k=vector_top_k, tax_year=period_filter, section_number=section_number)

        bm25_ids = [hit["chunk_id"] for hit in bm25_hits]
        vector_ids = [hit["chunk_id"] for hit in vector_hits]
        fused = reciprocal_rank_fusion(bm25_ids, vector_ids, k=60)

        result_map: Dict[str, Dict[str, Any]] = {}
        for hit in bm25_hits + vector_hits:
            chunk_id = hit["chunk_id"]
            normalized = self._normalize_result(hit)
            existing = result_map.get(chunk_id)
            if existing is None:
                result_map[chunk_id] = normalized
            else:
                existing["score"] = max(float(existing.get("score", 0.0)), float(normalized.get("score", 0.0)))
                existing["combined_score"] = max(float(existing.get("combined_score", 0.0)), float(normalized.get("combined_score", 0.0)))

        ranked = []
        for chunk_id, score in fused.items():
            hit = result_map.get(chunk_id)
            if not hit:
                continue
            hit["combined_score"] = float(score)
            hit["rank"] = len(ranked) + 1
            ranked.append(hit)

        for chunk_id, hit in result_map.items():
            if chunk_id not in fused:
                hit["combined_score"] = float(hit.get("score", 0.0))
                hit["rank"] = len(ranked) + 1
                ranked.append(hit)

        filtered = filter_hits_by_metadata(ranked, tax_year=period_filter, assessment_year=assessment_year, section_number=section_number)
        if rerank:
            self.reranker = Reranker(enabled=True)
            filtered = self.reranker.rerank(filtered, query)

        deduped: List[Dict[str, Any]] = []
        seen = set()
        for item in filtered:
            canonical = self._normalize_result(item)
            key = canonical.get("chunk_id") or canonical.get("document_id")
            if key in seen:
                continue
            seen.add(key)
            deduped.append(canonical)

        duration_ms = (time.time() - started) * 1000
        if duration_ms:
            pass

        return deduped[:top_k]

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi


class BM25Retriever:
    def __init__(self) -> None:
        self.documents: List[Dict[str, Any]] = []
        self.bm25 = None

    def _normalize(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s\-./]", " ", text)
        return [token for token in text.split() if token]

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = documents
        corpus = [self._normalize((doc.get("text") or "")) for doc in documents]
        self.bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int = 5, tax_year: Optional[str] = None, section_number: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.documents or not self.bm25:
            return []

        tokens = self._normalize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)
        ranked = []
        for idx, document in enumerate(self.documents):
            score = float(scores[idx])
            applicable_period = document.get("applicable_tax_year") or document.get("applicable_assessment_year")
            if tax_year and applicable_period and applicable_period != tax_year:
                score *= 0.4
            if section_number and document.get("section_number") and document["section_number"] != section_number:
                score *= 0.5
            ranked.append({
                "chunk_id": document.get("chunk_id"),
                "document_id": document.get("document_id"),
                "document_title": document.get("document_title"),
                "source_url": document.get("source_url"),
                "issuing_authority": document.get("issuing_authority"),
                "document_type": document.get("document_type"),
                "section_number": document.get("section_number"),
                "subsection_number": document.get("subsection_number"),
                "rule_number": document.get("rule_number"),
                "applicable_tax_year": document.get("applicable_tax_year") or document.get("applicable_assessment_year"),
                "source_version": document.get("source_version"),
                "score": float(score),
                "text": document.get("text"),
                "metadata": document,
                "retrieval_method": "bm25",
            })

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_k]

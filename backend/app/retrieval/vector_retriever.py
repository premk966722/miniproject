from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional


class VectorRetriever:
    def __init__(self, collection_name: str = "tax_documents") -> None:
        self.collection_name = collection_name
        self.documents: List[Dict[str, Any]] = []
        self._embeddings: Dict[str, List[float]] = {}

    def _embed_text(self, text: str) -> List[float]:
        value = text.lower().strip()
        if not value:
            return [0.0]
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        values = []
        for idx in range(0, 16):
            chunk = digest[idx:idx+2]
            values.append(float(int(chunk, 16) % 1000) / 1000.0)
        return values

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = documents
        self._embeddings = {doc.get("chunk_id"): self._embed_text(doc.get("text", "")) for doc in documents}

    def search(self, query: str, top_k: int = 5, tax_year: Optional[str] = None, section_number: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.documents:
            return []

        q_vec = self._embed_text(query)
        results = []
        for document in self.documents:
            vec = self._embeddings.get(document.get("chunk_id"), [0.0])
            score = sum(a * b for a, b in zip(q_vec, vec))
            applicable_period = document.get("applicable_tax_year") or document.get("applicable_assessment_year")
            if tax_year and applicable_period and applicable_period != tax_year:
                score *= 0.4
            if section_number and document.get("section_number") and document["section_number"] != section_number:
                score *= 0.5
            results.append({
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
                "retrieval_method": "vector",
            })
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]

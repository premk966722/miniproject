from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from app.retrieval.hybrid_retriever import HybridRetriever as _HybridRetriever


class HybridRetriever(_HybridRetriever):
    """Compatibility wrapper that preserves the original public API used by the app."""

    def search(self, query: str, tax_year: Optional[str] = None, top_k: int = 6, **kwargs: Any) -> List[Dict[str, Any]]:
        hits = super().search(
            query=query,
            tax_year=tax_year,
            assessment_year=kwargs.get("assessment_year"),
            section_number=kwargs.get("section_number"),
            top_k=top_k,
            bm25_top_k=kwargs.get("bm25_top_k", 10),
            vector_top_k=kwargs.get("vector_top_k", 10),
            rerank=kwargs.get("rerank", False),
        )
        for hit in hits:
            hit.setdefault("title", hit.get("document_title") or hit.get("title") or "Untitled")
            hit.setdefault("url", hit.get("source_url") or hit.get("url"))
            hit.setdefault("authority", hit.get("issuing_authority") or hit.get("authority") or "Unknown")
            hit.setdefault("metadata", hit.get("metadata") or hit)
        return hits


def build_seed_documents() -> List[Dict[str, Any]]:
    docs = [
        {
            "chunk_id": hashlib.sha256(b"seed-1").hexdigest()[:16],
            "document_id": "seed-doc-1",
            "document_title": "Official filing guidance: tax year and regime selection",
            "source_url": "https://www.incometax.gov.in/",
            "issuing_authority": "Income Tax Department",
            "document_type": "guidance",
            "act_name": "official guidance",
            "section_number": None,
            "subsection_number": None,
            "rule_number": None,
            "publication_date": None,
            "effective_from": None,
            "effective_to": None,
            "applicable_assessment_year": None,
            "applicable_tax_year": "2024-25",
            "source_version": "seed",
            "content_hash": hashlib.sha256(b"seed-1").hexdigest(),
            "authority_level": "official",
            "ingestion_timestamp": "2026-10-20T00:00:00Z",
            "text": "The relevant tax year and taxpayer status should be established before relying on a tax rule. Different filing and compliance obligations may apply depending on the assessment year, income type, and the applicable tax regime selected by the taxpayer.",
        },
        {
            "chunk_id": hashlib.sha256(b"seed-2").hexdigest()[:16],
            "document_id": "seed-doc-2",
            "document_title": "Official filing guidance: evidence and regime-specific compliance",
            "source_url": "https://www.incometaxindia.gov.in/",
            "issuing_authority": "Income Tax Department",
            "document_type": "guidance",
            "act_name": "official guidance",
            "section_number": None,
            "subsection_number": None,
            "rule_number": None,
            "publication_date": None,
            "effective_from": None,
            "effective_to": None,
            "applicable_assessment_year": None,
            "applicable_tax_year": "2025-26",
            "source_version": "seed",
            "content_hash": hashlib.sha256(b"seed-2").hexdigest(),
            "authority_level": "official",
            "ingestion_timestamp": "2026-10-20T00:00:00Z",
            "text": "A defensible answer should cite the governing source, the relevant tax period, and any conditions or exclusions that change applicability. Where the evidence is incomplete or contradictory, the answer should be qualified rather than asserted with certainty.",
        },
        {
            "chunk_id": hashlib.sha256(b"seed-3").hexdigest()[:16],
            "document_id": "seed-doc-3",
            "document_title": "Official guidance: document provenance and uncertainty",
            "source_url": "https://www.incometax.gov.in/",
            "issuing_authority": "Income Tax Department",
            "document_type": "guidance",
            "act_name": "official guidance",
            "section_number": None,
            "subsection_number": None,
            "rule_number": None,
            "publication_date": None,
            "effective_from": None,
            "effective_to": None,
            "applicable_assessment_year": None,
            "applicable_tax_year": "2023-24",
            "source_version": "seed",
            "content_hash": hashlib.sha256(b"seed-3").hexdigest(),
            "authority_level": "official",
            "ingestion_timestamp": "2026-10-20T00:00:00Z",
            "text": "Evidence quality matters. A rule is stronger when it comes from a recognized official source and the applicable tax period is clearly identified. Unsupported answers, assumptions, and missing facts should be stated transparently.",
        },
    ]
    return docs

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.ingestion.source_registry import is_allowed_url


@dataclass
class CitationRecord:
    citation_id: str
    document_id: str
    chunk_id: str
    document_title: str
    issuing_authority: str
    url: str
    section_identifier: str
    supporting_passage: str
    source_version: str
    applicable_period: Optional[str]
    provenance_status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "document_title": self.document_title,
            "issuing_authority": self.issuing_authority,
            "url": self.url,
            "section_identifier": self.section_identifier,
            "supporting_passage": self.supporting_passage,
            "source_version": self.source_version,
            "applicable_period": self.applicable_period,
            "provenance_status": self.provenance_status,
        }


class CitationManager:
    def create_citation(self, evidence: Dict[str, Any]) -> CitationRecord:
        source = evidence.get("metadata") or evidence
        text = source.get("text") or evidence.get("text") or ""
        seed = f"{source.get('document_id') or evidence.get('document_id')}::{source.get('chunk_id') or evidence.get('chunk_id')}::{source.get('source_url') or evidence.get('source_url')}"
        citation_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        url = source.get("source_url") or evidence.get("source_url") or ""
        return CitationRecord(
            citation_id=citation_id,
            document_id=source.get("document_id") or evidence.get("document_id") or "unknown",
            chunk_id=source.get("chunk_id") or evidence.get("chunk_id") or "unknown",
            document_title=source.get("document_title") or evidence.get("document_title") or "Untitled",
            issuing_authority=source.get("issuing_authority") or evidence.get("issuing_authority") or "Unknown",
            url=url,
            section_identifier=source.get("section_number") or evidence.get("section_number") or "General guidance",
            supporting_passage=text[:300],
            source_version=source.get("source_version") or evidence.get("source_version") or "unknown",
            applicable_period=(
                source.get("applicable_assessment_year")
                or source.get("applicable_tax_year")
                or evidence.get("applicable_assessment_year")
                or evidence.get("applicable_tax_year")
            ),
            provenance_status="source_allowlisted",
        )

    def validate_citation(self, citation: CitationRecord, evidence: Optional[Dict[str, Any]] = None) -> bool:
        if not citation or not citation.citation_id:
            return False
        if not citation.document_id or not citation.chunk_id:
            return False
        if not citation.url or not is_allowed_url(citation.url):
            return False
        if evidence is not None:
            source = evidence.get("metadata") or evidence
            if citation.document_id != (source.get("document_id") or evidence.get("document_id")):
                return False
            if citation.chunk_id != (source.get("chunk_id") or evidence.get("chunk_id")):
                return False
            if citation.url != (source.get("source_url") or source.get("url")):
                return False
            actual_text = source.get("text") or evidence.get("text") or ""
            if not actual_text.startswith(citation.supporting_passage):
                return False
        return True

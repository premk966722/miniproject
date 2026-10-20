from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SourceRecord:
    source_id: str
    official_domain: str
    source_url: str
    source_category: str
    issuing_authority: str
    document_type: str
    ingestion_status: str = "not_started"
    last_successful_fetch: Optional[str] = None
    last_attempted_fetch: Optional[str] = None
    content_hash: Optional[str] = None
    publication_date: Optional[str] = None
    source_version: Optional[str] = None
    error_info: Optional[str] = None
    enabled: bool = True


@dataclass
class ChunkRecord:
    chunk_id: str
    document_id: str
    document_title: str
    source_url: str
    issuing_authority: str
    document_type: str
    act_name: str
    section_number: Optional[str]
    subsection_number: Optional[str]
    rule_number: Optional[str]
    publication_date: Optional[str]
    effective_from: Optional[str]
    effective_to: Optional[str]
    applicable_assessment_year: Optional[str]
    applicable_tax_year: Optional[str]
    source_version: Optional[str]
    content_hash: str
    authority_level: str
    ingestion_timestamp: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalHit:
    chunk_id: str
    document_id: str
    title: str
    text: str
    url: str
    authority: str
    source_type: str
    score: float
    section_number: Optional[str] = None
    publication_date: Optional[str] = None
    source_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

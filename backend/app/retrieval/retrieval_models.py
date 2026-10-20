from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RetrievalResult:
    chunk_id: str
    document_id: str
    document_title: str
    source_url: str
    issuing_authority: str
    document_type: str
    section_number: Optional[str]
    subsection_number: Optional[str] = None
    rule_number: Optional[str] = None
    applicable_tax_year: Optional[str] = None
    source_version: Optional[str] = None
    retrieval_method: str = "hybrid"
    original_rank: int = 0
    score: float = 0.0
    combined_score: float = 0.0
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryAnalysis:
    topic: str
    section_number: Optional[str] = None
    tax_year: Optional[str] = None
    assessment_year: Optional[str] = None
    regime: Optional[str] = None
    income_category: Optional[str] = None
    taxpayer_category: Optional[str] = None
    missing_information: List[str] = field(default_factory=list)
    needs_clarification: bool = False
    query_type: str = "general"


@dataclass
class RetrievalDiagnostics:
    bm25_count: int = 0
    vector_count: int = 0
    fused_count: int = 0
    applied_filters: Dict[str, Any] = field(default_factory=dict)
    rejected_results: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    rerank_enabled: bool = False
    reranked_count: int = 0
    missing_tax_year_metadata: List[str] = field(default_factory=list)


@dataclass
class RetrievalRequest:
    question: str
    assessment_year: Optional[str] = None
    tax_year: Optional[str] = None
    regime: Optional[str] = None
    section_number: Optional[str] = None
    top_k: int = 5
    bm25_top_k: int = 10
    vector_top_k: int = 10
    rerank: bool = False

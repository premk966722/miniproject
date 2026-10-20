from __future__ import annotations

from app.evidence.validator import validate_evidence
from app.generation.answer import generate_answer
from app.ingestion.source_registry import ensure_default_sources, is_allowed_url
from app.retrieval.hybrid import HybridRetriever, build_seed_documents


def test_allowed_url_check() -> None:
    assert is_allowed_url("https://www.incometax.gov.in/") is True
    assert is_allowed_url("https://example.com/") is False


def test_setup_registers_default_sources() -> None:
    sources = ensure_default_sources()
    assert len(sources) >= 2
    assert any(source["source_id"] == "incometax-gov-home" for source in sources)


def test_hybrid_retrieval_returns_hits() -> None:
    retriever = HybridRetriever()
    retriever.index_documents(build_seed_documents())
    hits = retriever.search("tax year and regime selection", tax_year="2024-25")
    assert len(hits) >= 1
    assert hits[0]["title"]


def test_evidence_validation_handles_missing_evidence() -> None:
    result = validate_evidence([], "What is the tax treatment?")
    assert result["status"] == "insufficient_evidence"


def test_generate_answer_contains_citations() -> None:
    retriever = HybridRetriever()
    retriever.index_documents(build_seed_documents())
    hits = retriever.search("official guidance on tax year and regime selection", tax_year="2024-25")
    answer = generate_answer("What should I check before filing?", hits, tax_year="2024-25")
    assert answer["needs_clarification"] is False
    assert len(answer["citations"]) >= 1

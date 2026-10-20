from __future__ import annotations

from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.metadata_filter import filter_hits_by_metadata
from app.retrieval.query_analyzer import analyze_query
from app.retrieval.rrf import reciprocal_rank_fusion


DOCS = [
    {
        "chunk_id": "chunk-1",
        "document_id": "doc-1",
        "document_title": "Section 80C deduction",
        "source_url": "https://www.incometax.gov.in/",
        "issuing_authority": "Income Tax Department",
        "document_type": "official",
        "act_name": "Income-tax Act, 1961",
        "section_number": "80C",
        "subsection_number": None,
        "rule_number": None,
        "publication_date": "2024-01-01",
        "effective_from": None,
        "effective_to": None,
        "applicable_assessment_year": "2024-25",
        "applicable_tax_year": "2024-25",
        "source_version": "v1",
        "content_hash": "hash-1",
        "authority_level": "official",
        "ingestion_timestamp": "2024-01-01T00:00:00Z",
        "text": "Section 80C allows a deduction for certain eligible investments and payments subject to conditions and limits.",
    },
    {
        "chunk_id": "chunk-2",
        "document_id": "doc-2",
        "document_title": "Section 80CCD contribution",
        "source_url": "https://www.incometaxindia.gov.in/",
        "issuing_authority": "Income Tax Department",
        "document_type": "official",
        "act_name": "Income-tax Act, 1961",
        "section_number": "80CCD",
        "subsection_number": None,
        "rule_number": None,
        "publication_date": "2024-01-01",
        "effective_from": None,
        "effective_to": None,
        "applicable_assessment_year": "2023-24",
        "applicable_tax_year": "2023-24",
        "source_version": "v2",
        "content_hash": "hash-2",
        "authority_level": "official",
        "ingestion_timestamp": "2024-01-01T00:00:00Z",
        "text": "Section 80CCD deals with employee contributions to the National Pension System and related limits.",
    },
    {
        "chunk_id": "chunk-3",
        "document_id": "doc-3",
        "document_title": "Old versus new tax regime",
        "source_url": "https://www.incometax.gov.in/",
        "issuing_authority": "Income Tax Department",
        "document_type": "guidance",
        "act_name": "official guidance",
        "section_number": None,
        "subsection_number": None,
        "rule_number": None,
        "publication_date": "2024-01-01",
        "effective_from": None,
        "effective_to": None,
        "applicable_assessment_year": "2024-25",
        "applicable_tax_year": "2024-25",
        "source_version": "v1",
        "content_hash": "hash-3",
        "authority_level": "official",
        "ingestion_timestamp": "2024-01-01T00:00:00Z",
        "text": "Taxpayers may choose the old or new regime depending on eligibility and the applicable tax year.",
    },
]


def test_query_analysis_extracts_year_and_regime() -> None:
    analysis = analyze_query("What is the deduction under section 80C for the 2024-25 old regime?")
    assert analysis["tax_year"] == "2024-25"
    assert analysis["section_number"] == "80C"
    assert analysis["regime"] == "old"
    assert analysis["needs_clarification"] is False


def test_hybrid_retrieval_filters_explicit_assessment_year() -> None:
    docs = [{**DOCS[0], "applicable_tax_year": None, "applicable_assessment_year": "2024-25"}]
    retriever = HybridRetriever(docs)
    hits = retriever.search("What does section 80C say for AY 2024-25?", top_k=5)
    assert hits
    assert hits[0]["chunk_id"] == "chunk-1"


def test_bm25_exact_match_returns_section_result() -> None:
    retriever = BM25Retriever()
    retriever.index_documents(DOCS)
    hits = retriever.search("Section 80C deduction", top_k=5)
    assert hits[0]["chunk_id"] == "chunk-1"
    assert hits[0]["section_number"] == "80C"


def test_metadata_filter_uses_tax_year_and_section() -> None:
    hits = [
        {"chunk_id": "chunk-1", "metadata": {"applicable_tax_year": "2024-25", "section_number": "80C"}},
        {"chunk_id": "chunk-2", "metadata": {"applicable_tax_year": "2023-24", "section_number": "80CCD"}},
    ]
    filtered = filter_hits_by_metadata(hits, tax_year="2024-25", section_number="80C")
    assert [item["chunk_id"] for item in filtered] == ["chunk-1"]


def test_metadata_filter_matches_assessment_year_when_tax_year_missing() -> None:
    hits = [
        {"chunk_id": "ay-match", "metadata": {"applicable_assessment_year": "2024-25", "section_number": "80C"}},
        {"chunk_id": "ay-other", "metadata": {"applicable_assessment_year": "2023-24", "section_number": "80C"}},
    ]
    filtered = filter_hits_by_metadata(hits, tax_year="2024-25")
    assert [item["chunk_id"] for item in filtered] == ["ay-match"]


def test_rrf_combines_ranks_with_known_scores() -> None:
    ranked_a = ["chunk-1", "chunk-2"]
    ranked_b = ["chunk-2", "chunk-1"]
    scores = reciprocal_rank_fusion(ranked_a, ranked_b, k=60)
    assert "chunk-1" in scores
    assert "chunk-2" in scores
    assert scores["chunk-1"] > scores["chunk-2"]


def test_hybrid_retriever_deduplicates_and_preserves_metadata() -> None:
    retriever = HybridRetriever()
    retriever.index_documents(DOCS)
    hits = retriever.search("section 80C deduction", tax_year="2024-25", top_k=5)
    assert len(hits) >= 1
    assert hits[0]["chunk_id"] == "chunk-1"
    assert hits[0]["metadata"]["document_title"] == "Section 80C deduction"

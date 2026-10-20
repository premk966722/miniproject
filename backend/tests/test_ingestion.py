from __future__ import annotations

from app.ingestion.document_cleaner import clean_extracted_text
from app.ingestion.document_versioning import compute_content_hash, detect_document_change
from app.ingestion.legal_chunker import chunk_legal_text
from app.ingestion.source_fetcher import is_allowed_url


def test_source_fetcher_allowlist() -> None:
    assert is_allowed_url("https://www.incometax.gov.in/") is True
    assert is_allowed_url("http://localhost:8000/") is False
    assert is_allowed_url("https://example.com/") is False


def test_document_versioning_detects_change() -> None:
    old_text = "Section 80C. Deduction as per the Act."
    new_text = "Section 80C. Deduction under a revised rule."
    old_hash = compute_content_hash(old_text)
    new_hash = compute_content_hash(new_text)
    assert old_hash != new_hash
    assert detect_document_change(old_hash, new_hash) is True


def test_document_cleaner_preserves_statutory_language() -> None:
    dirty = "HEADER\nSection 80C. Subject to conditions, the deduction is allowed.\nHEADER\nProviso: Nothing in this section shall apply."
    cleaned = clean_extracted_text(dirty)
    assert "Section 80C" in cleaned
    assert "Proviso" in cleaned
    assert "HEADER" not in cleaned


def test_legal_chunker_keeps_boundary_markers() -> None:
    text = "Section 80C. This deduction is available.\n\nSection 80CCD. The contribution limit applies."
    chunks = chunk_legal_text(text)
    assert len(chunks) >= 2
    assert any("Section 80C" in chunk for chunk in chunks)
    assert any("Section 80CCD" in chunk for chunk in chunks)

from __future__ import annotations

from pathlib import Path

import pytest

from app import db
from app.ingestion import ingestion_service


HTML = b"<html><head><title>Official Tax Circular</title></head><body><main><h1>Section 80C</h1><p>Eligible amounts are subject to the conditions stated in this provision.</p></main></body></html>"


def test_successful_ingestion_persists_chunks_and_unchanged_sync_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tax.sqlite3")
    monkeypatch.setattr(ingestion_service, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(ingestion_service, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(ingestion_service, "METADATA_DIR", tmp_path / "metadata")
    ingestion_service.RAW_DIR.mkdir()
    ingestion_service.PROCESSED_DIR.mkdir()
    ingestion_service.METADATA_DIR.mkdir()
    db.init_db()
    db.insert_source({
        "source_id": "test-source",
        "official_domain": "www.incometax.gov.in",
        "source_url": "https://www.incometax.gov.in/test.html",
        "enabled": True,
        "ingestion_status": "ready",
    })
    monkeypatch.setattr(ingestion_service, "fetch_url", lambda *args, **kwargs: {
        "status": "ok",
        "url": "https://www.incometax.gov.in/iec/foportal/test.html",
        "content_type": "text/html",
        "body": HTML,
    })

    first = ingestion_service.ingest_source_document(
        "test-source", "https://www.incometax.gov.in/test.html"
    )
    assert first["status"] == "success"
    assert first["chunk_count"] >= 1
    assert len(db.list_index_documents()) == first["chunk_count"]
    assert db.list_index_documents()[0]["document_title"] == "Official Tax Circular"
    assert db.list_index_documents()[0]["source_url"] == "https://www.incometax.gov.in/iec/foportal/test.html"

    second = ingestion_service.ingest_source_document(
        "test-source", "https://www.incometax.gov.in/test.html"
    )
    assert second["status"] == "unchanged"
    assert len(db.list_index_documents()) == first["chunk_count"]


def test_failed_source_sync_keeps_last_successful_hash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tax.sqlite3")
    db.init_db()
    previous = {
        "source_id": "preserve-me",
        "official_domain": "www.incometax.gov.in",
        "source_url": "https://www.incometax.gov.in/",
        "enabled": True,
        "ingestion_status": "success",
        "content_hash": "last-good-hash",
        "last_successful_fetch": "2026-01-01T00:00:00Z",
    }
    db.insert_source(previous)
    monkeypatch.setattr(
        ingestion_service,
        "ingest_source_document",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("temporary fetch failure")),
    )

    report = ingestion_service.ingest_registered_sources()
    source = next(row for row in db.list_sources() if row["source_id"] == "preserve-me")
    result = next(item for item in report["results"] if item["source_id"] == "preserve-me")
    assert result["status"] == "error"
    assert source["content_hash"] == "last-good-hash"
    assert source["last_successful_fetch"] == "2026-01-01T00:00:00Z"


def test_assessment_year_in_official_filename_is_recorded_not_guessed() -> None:
    assert ingestion_service._assessment_year_from_source_url(
        "https://www.incometax.gov.in/forms/FAQ%20AY%202024-25.pdf"
    ) == "2024-25"
    assert ingestion_service._assessment_year_from_source_url(
        "https://www.incometax.gov.in/forms/current-rules.pdf"
    ) is None

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from app.config import DATA_DIR
from app.db import insert_chunk, insert_source, list_sources, store_document
from app.ingestion.document_cleaner import clean_extracted_text
from app.ingestion.document_extractor import extract_document_metadata, extract_document_text
from app.ingestion.document_versioning import compute_content_hash, detect_document_change
from app.ingestion.legal_chunker import chunk_legal_text
from app.ingestion.source_fetcher import fetch_url
from app.ingestion.source_registry import is_allowed_url

DATA_ROOT = DATA_DIR
RAW_DIR = DATA_ROOT / "raw"
PROCESSED_DIR = DATA_ROOT / "processed"
METADATA_DIR = DATA_ROOT / "metadata"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ingest_source_document(
    source_id: str,
    source_url: str,
    document_title: str = "Official tax document",
    document_type: str = "official",
    authority: str = "Income Tax Department",
    category: str = "official",
    source_version: Optional[str] = None,
) -> Dict[str, Any]:
    if not is_allowed_url(source_url):
        raise ValueError(f"Source URL is not approved for ingestion: {source_url}")

    now = _utc_now()
    source_record = next((row for row in list_sources() if row["source_id"] == source_id), None)
    prior_hash = source_record["content_hash"] if source_record else None

    fetch_result = fetch_url(source_url, timeout=20)
    if fetch_result.get("status") == "not_modified":
        return {
            "status": "unchanged",
            "source_id": source_id,
            "source_url": source_url,
            "content_hash": prior_hash,
            "ingestion_timestamp": now,
            "note": "Document not modified since the last successful fetch.",
        }

    content_type = fetch_result.get("content_type", "")
    resolved_source_url = fetch_result.get("url") or source_url
    payload = fetch_result.get("body", b"")
    text, doc_type = extract_document_text(source_url, content_type, payload)
    cleaned = clean_extracted_text(text)
    chunks = chunk_legal_text(cleaned)
    content_hash = compute_content_hash(cleaned)

    if not cleaned or len(chunks) == 0:
        raise ValueError(f"Extraction produced no usable content for {source_url}")

    changed = detect_document_change(prior_hash, content_hash)
    if not changed:
        return {
            "status": "unchanged",
            "source_id": source_id,
            "source_url": source_url,
            "content_hash": content_hash,
            "ingestion_timestamp": now,
            "note": "Fetched content matches the last successfully indexed version.",
        }
    document_id = hashlib.sha256(f"{source_id}:{resolved_source_url}:{content_hash}".encode("utf-8")).hexdigest()[:32]
    raw_path = RAW_DIR / f"{document_id}.raw"
    processed_path = PROCESSED_DIR / f"{document_id}.txt"
    metadata_path = METADATA_DIR / f"{document_id}.json"

    raw_path.write_bytes(payload)
    processed_path.write_text(cleaned, encoding="utf-8")
    extracted_metadata = extract_document_metadata(resolved_source_url, payload.decode("utf-8", errors="replace") if "html" in content_type.lower() else None)
    document_title = extracted_metadata.get("title") or document_title
    document_metadata = {
        "document_id": document_id,
        "document_title": document_title,
        "source_url": resolved_source_url,
        "issuing_authority": authority,
        "document_type": document_type,
        "act_name": category,
        "source_version": source_version or "v1",
        "applicable_assessment_year": _assessment_year_from_source_url(resolved_source_url),
        "content_hash": content_hash,
        "ingestion_timestamp": now,
        "ingestion_status": "success",
    }
    metadata_path.write_text(json.dumps(document_metadata, indent=2), encoding="utf-8")

    store_document(document_id, source_id, document_title, resolved_source_url, document_type, content_hash, None, str(raw_path), str(processed_path), document_metadata)
    for index, chunk_text in enumerate(chunks):
        chunk_id = hashlib.sha256(f"{document_id}:{index}:{chunk_text}".encode("utf-8")).hexdigest()[:32]
        insert_chunk(chunk_id, document_id, chunk_text, {
            **document_metadata,
            "chunk_id": chunk_id,
            "section_number": None,
            "applicable_tax_year": None,
            "applicable_assessment_year": document_metadata.get("applicable_assessment_year"),
            "authority_level": "official",
        })

    insert_source({
        "source_id": source_id,
        "official_domain": source_url.split("//")[-1].split("/")[0],
        "source_url": source_url,
        "source_category": category,
        "issuing_authority": authority,
        "document_type": document_type,
        "ingestion_status": "success",
        "last_successful_fetch": now,
        "last_attempted_fetch": now,
        "content_hash": content_hash,
        "publication_date": None,
        "source_version": source_version or "v1",
        "error_info": None,
        "enabled": True,
    })

    return {
        "status": "success",
        "source_id": source_id,
        "document_id": document_id,
        "document_title": document_title,
        "source_url": source_url,
        "content_hash": content_hash,
        "changed": changed,
        "chunk_count": len(chunks),
        "ingestion_timestamp": now,
        "document_type": doc_type,
    }


def _assessment_year_from_source_url(url: str) -> Optional[str]:
    """Extract an explicitly named AY from the official source path; never infer one from fetch date."""
    match = re.search(r"\bAY\s*(20\d{2}-\d{2})\b", unquote(url), flags=re.IGNORECASE)
    return match.group(1) if match else None


def ingest_registered_sources() -> Dict[str, Any]:
    rows = list_sources()
    results = []
    for row in rows:
        if row.get("enabled"):
            try:
                result = ingest_source_document(
                    source_id=row["source_id"],
                    source_url=row["source_url"],
                    document_title=row.get("source_url", "Official source"),
                    document_type=row.get("document_type", "official"),
                    authority=row.get("issuing_authority", "Income Tax Department"),
                    category=row.get("source_category", "official"),
                    source_version=row.get("source_version"),
                )
            except Exception as exc:
                insert_source({**row, "ingestion_status": "error", "last_attempted_fetch": _utc_now(), "error_info": str(exc)[:500]})
                result = {"status": "error", "source_id": row["source_id"], "error": str(exc)[:500]}
            results.append(result)
    return {"status": "completed", "processed": len(results), "results": results}

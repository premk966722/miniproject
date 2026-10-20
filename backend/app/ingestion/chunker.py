from __future__ import annotations

import hashlib
from typing import Any, Dict, List


def split_into_paragraphs(text: str) -> List[str]:
    blocks = []
    for block in text.replace("\r", "\n").split("\n\n"):
        cleaned = " ".join(block.split())
        if cleaned:
            blocks.append(cleaned)
    return blocks


def create_chunks(title: str, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    paragraphs = split_into_paragraphs(text)
    chunks = []
    for index, paragraph in enumerate(paragraphs):
        chunk_text = paragraph[:1800]
        chunk_id = hashlib.sha256(f"{metadata.get('document_id')}:{index}:{chunk_text}".encode("utf-8")).hexdigest()[:32]
        chunk = {
            "chunk_id": chunk_id,
            "document_id": metadata.get("document_id"),
            "document_title": title,
            "source_url": metadata.get("source_url"),
            "issuing_authority": metadata.get("issuing_authority", "unknown"),
            "document_type": metadata.get("document_type", "official"),
            "act_name": metadata.get("act_name", "unknown"),
            "section_number": metadata.get("section_number"),
            "subsection_number": metadata.get("subsection_number"),
            "rule_number": metadata.get("rule_number"),
            "publication_date": metadata.get("publication_date"),
            "effective_from": metadata.get("effective_from"),
            "effective_to": metadata.get("effective_to"),
            "applicable_assessment_year": metadata.get("applicable_assessment_year"),
            "applicable_tax_year": metadata.get("applicable_tax_year"),
            "source_version": metadata.get("source_version"),
            "content_hash": hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
            "authority_level": metadata.get("authority_level", "official"),
            "ingestion_timestamp": metadata.get("ingestion_timestamp"),
            "text": chunk_text,
        }
        chunks.append(chunk)
    return chunks

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse
from typing import Any, Dict, List

from app.db import insert_source, list_sources

ALLOWED_DOMAINS = {
    "incometax.gov.in",
    "www.incometax.gov.in",
    "incometaxindia.gov.in",
    "www.incometaxindia.gov.in",
}

DEFAULT_SOURCES = [
    {
        "source_id": "incometax-gov-home",
        "official_domain": "incometax.gov.in",
        "source_url": "https://www.incometax.gov.in/",
        "source_category": "official",
        "issuing_authority": "Income Tax Department",
        "document_type": "portal",
        "ingestion_status": "ready",
        "last_successful_fetch": None,
        "last_attempted_fetch": None,
        "content_hash": None,
        "publication_date": None,
        "source_version": "initial",
        "error_info": None,
        "enabled": True,
    },
    {
        "source_id": "incometaxindia-home",
        "official_domain": "incometaxindia.gov.in",
        "source_url": "https://www.incometaxindia.gov.in/",
        "source_category": "official",
        "issuing_authority": "Income Tax Department",
        "document_type": "portal",
        "ingestion_status": "ready",
        "last_successful_fetch": None,
        "last_attempted_fetch": None,
        "content_hash": None,
        "publication_date": None,
        "source_version": "initial",
        "error_info": None,
        "enabled": True,
    },
    {
        "source_id": "incometax-itr-faq-ay-2024-25",
        "official_domain": "www.incometax.gov.in",
        "source_url": "https://www.incometax.gov.in/iec/foportal/sites/default/files/2024-06/Common%20ITR%20Filing%20FAQs%20AY%202024-25.pdf",
        "source_category": "official filing guidance",
        "issuing_authority": "Income Tax Department",
        "document_type": "official FAQ PDF",
        "ingestion_status": "ready",
        "last_successful_fetch": None,
        "last_attempted_fetch": None,
        "content_hash": None,
        "publication_date": "2024-06",
        "source_version": "AY 2024-25 FAQ",
        "error_info": None,
        "enabled": True,
    },
]


def is_private_or_local(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        pass
    return hostname in {"localhost", "127.0.0.1", "0.0.0.0"}


def is_allowed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return False
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False
    if is_private_or_local(hostname):
        return False
    try:
        if parsed.port not in (None, 443):
            return False
    except ValueError:
        return False
    return hostname in ALLOWED_DOMAINS or hostname.endswith(".incometax.gov.in") or hostname.endswith(".incometaxindia.gov.in")




def ensure_default_sources() -> List[Dict[str, Any]]:
    from app.db import init_db

    init_db()
    existing = {row["source_id"] for row in list_sources()}
    for source in DEFAULT_SOURCES:
        if source["source_id"] not in existing:
            insert_source(source)
    return list_sources()


def sync_sources() -> Dict[str, Any]:
    sources = list_sources()
    active = [s for s in sources if s["enabled"]]
    return {
        "processed": len(active),
        "status": "registered",
        "sources": active,
        "note": "This vertical slice uses a controlled allowlist and avoids crawling unapproved domains.",
    }

from __future__ import annotations

from typing import Any, Dict, List

from app.ingestion.source_registry import ALLOWED_DOMAINS


def validate_evidence(hits: List[Dict[str, Any]], query: str, tax_year: str | None = None) -> Dict[str, Any]:
    if not hits:
        return {
            "status": "insufficient_evidence",
            "reason": "No indexed evidence matched the question.",
            "sufficient": False,
            "authoritative": False,
        }

    domains = []
    for hit in hits:
        if hit.get("url"):
            domain = hit["url"].split("//")[-1].split("/")[0].lower()
            domains.append(domain)

    authoritative = all(any(allowed in domain for allowed in ALLOWED_DOMAINS) for domain in domains)
    relevant = any(len(query.split()) >= 3 for _ in hits)
    if tax_year:
        year_match = any(hit.get("metadata", {}).get("applicable_tax_year") in {tax_year, None} for hit in hits)
    else:
        year_match = True

    status = "sufficient" if authoritative and year_match and relevant else "needs_clarification"
    return {
        "status": status,
        "reason": "Evidence was checked for authority, relevance, and applicable tax period.",
        "sufficient": status == "sufficient",
        "authoritative": authoritative,
        "year_match": year_match,
    }

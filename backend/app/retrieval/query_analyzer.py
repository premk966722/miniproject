from __future__ import annotations

import re
from typing import Any, Dict, List

from app.retrieval.retrieval_models import QueryAnalysis


SECTION_PATTERNS = [
    re.compile(r"(?:section|sec\.?|s\.)\s*([A-Za-z0-9.\-/]+)", re.IGNORECASE),
    re.compile(r"(?:rule|notification|circular)\s*([A-Za-z0-9.\-/]+)", re.IGNORECASE),
]
YEAR_PATTERNS = [
    re.compile(r"\b(20\d{2}-\d{2}|20\d{2}/\d{2}|20\d{2})\b"),
    re.compile(r"\b(assessment\s*year\s*(?:of\s*)?(20\d{2}-\d{2}|20\d{2}))\b", re.IGNORECASE),
    re.compile(r"\b(tax\s*year\s*(?:of\s*)?(20\d{2}-\d{2}|20\d{2}))\b", re.IGNORECASE),
]
REGIME_PATTERNS = {
    "old": re.compile(r"\bold\s+regime\b", re.IGNORECASE),
    "new": re.compile(r"\bnew\s+regime\b", re.IGNORECASE),
}


def analyze_query(question: str) -> Dict[str, Any]:
    normalized = (question or "").strip()
    topic = normalized
    section_number = None
    for pattern in SECTION_PATTERNS:
        match = pattern.search(normalized)
        if match:
            section_number = match.group(1).strip()
            break

    tax_year = None
    assessment_year = None
    for pattern in YEAR_PATTERNS:
        match = pattern.search(normalized)
        if match:
            candidate = match.group(1)
            tax_year = candidate.replace("/", "-")
            if "assessment" in normalized.lower() or "assessment year" in normalized.lower():
                assessment_year = candidate.replace("/", "-")
            break

    regime = None
    for key, pattern in REGIME_PATTERNS.items():
        if pattern.search(normalized):
            regime = key
            break

    missing_information: List[str] = []
    if not tax_year and "year" in normalized.lower():
        missing_information.append("tax_year")
    if "regime" in normalized.lower() and not regime:
        missing_information.append("regime")

    needs_clarification = False
    if not tax_year and ("tax year" in normalized.lower() or "assessment year" in normalized.lower() or "year" in normalized.lower()):
        needs_clarification = True

    query_type = "calculation" if any(token in normalized.lower() for token in ["deduction", "slab", "taxable", "compute"]) else "general"

    result = QueryAnalysis(
        topic=topic,
        section_number=section_number,
        tax_year=tax_year,
        assessment_year=assessment_year or tax_year,
        regime=regime,
        income_category=None,
        taxpayer_category=None,
        missing_information=missing_information,
        needs_clarification=needs_clarification,
        query_type=query_type,
    )
    return result.__dict__

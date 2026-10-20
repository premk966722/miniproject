from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def filter_hits_by_metadata(
    hits: Iterable[Dict[str, Any]],
    tax_year: Optional[str] = None,
    assessment_year: Optional[str] = None,
    section_number: Optional[str] = None,
    act_name: Optional[str] = None,
    document_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for item in hits:
        metadata = item.get("metadata") or item
        if assessment_year:
            applicable = metadata.get("applicable_assessment_year") or metadata.get("applicable_tax_year")
            if applicable and str(applicable) != str(assessment_year):
                continue
        elif tax_year:
            applicable = metadata.get("applicable_tax_year") or metadata.get("applicable_assessment_year")
            if applicable and str(applicable) != str(tax_year):
                continue
        if section_number:
            if metadata.get("section_number") and str(metadata.get("section_number")) != str(section_number):
                continue
        if act_name and metadata.get("act_name") and str(metadata.get("act_name")) != str(act_name):
            continue
        if document_type and metadata.get("document_type") and str(metadata.get("document_type")) != str(document_type):
            continue
        filtered.append(item)
    return filtered

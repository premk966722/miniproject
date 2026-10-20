from __future__ import annotations

from typing import Any, Dict, List

from app.tax.applicability_validator import ApplicabilityStatus, ApplicabilityValidator


class EvidenceSelector:
    def select(
        self,
        question: str,
        tax_period: str | None,
        candidate_hits: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        validator = ApplicabilityValidator()
        supporting: List[Dict[str, Any]] = []
        excluded: List[Dict[str, Any]] = []
        conflicts: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for hit in candidate_hits:
            chunk_id = hit.get("chunk_id") or hit.get("document_id") or "unknown"
            if chunk_id in seen:
                continue
            seen.add(chunk_id)

            result = validator.validate(hit, requested_period=tax_period)
            entry = {
                "chunk_id": chunk_id,
                "document_id": hit.get("document_id"),
                "document_title": hit.get("document_title") or hit.get("title"),
                "source_url": hit.get("source_url") or hit.get("url"),
                "section_number": hit.get("section_number"),
                "text": hit.get("text"),
                "status": result.status.value,
                "reasons": result.reasons,
                "metadata": hit,
            }
            if result.status == ApplicabilityStatus.SUPPORTED:
                supporting.append(entry)
            elif result.status in {ApplicabilityStatus.POTENTIALLY_SUPERSEDED, ApplicabilityStatus.CONFLICTING}:
                conflicts.append(entry)
                excluded.append(entry)
            elif result.status == ApplicabilityStatus.NOT_APPLICABLE:
                excluded.append(entry)
            else:
                excluded.append(entry)

        selected = []
        for item in supporting:
            if tax_period and item["metadata"].get("applicable_tax_year") and item["metadata"].get("applicable_tax_year") != tax_period:
                continue
            selected.append(item)

        can_answer = bool(selected)
        return {
            "supporting_evidence": selected,
            "excluded_evidence": excluded,
            "conflicting_evidence": conflicts,
            "missing_evidence_requirements": [] if can_answer else ["No evidence with consistent applicability was selected for the requested period."],
            "can_answer": can_answer,
            "needs_clarification": not can_answer,
            "question": question,
            "tax_period": tax_period,
        }

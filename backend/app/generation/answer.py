from __future__ import annotations

from typing import Any, Dict, List

from app.evidence.validator import validate_evidence


def generate_answer(question: str, hits: List[Dict[str, Any]], tax_year: str | None = None, regime: str | None = None) -> Dict[str, Any]:
    validation = validate_evidence(hits, question, tax_year)
    if not hits or not validation["sufficient"]:
        return {
            "answer": "I could not find enough authoritative evidence to answer this confidently. Please provide a tax year and the relevant taxpayer circumstances, or rephrase the question with more specific details.",
            "citations": [],
            "confidence": "low",
            "needs_clarification": True,
            "status": validation["status"],
        }

    evidence_text = " ".join(hit["text"] for hit in hits[:3])
    summary = (
        "Based on the retrieved official-source guidance, the answer depends on the tax year, the taxpayer profile, and the relevant regime or conditions. "
        f"The evidence reviewed indicates that {evidence_text[:350]}"
    )
    if tax_year:
        summary += f" This should be interpreted for the {tax_year} tax year."
    if regime:
        summary += f" The question appears to be asked in the context of the {regime} regime."

    citations = [
        {
            "title": hit["title"],
            "authority": hit["authority"],
            "url": hit["url"],
            "section": hit.get("section_number") or "General guidance",
            "passage": hit["text"][:250],
        }
        for hit in hits[:3]
    ]
    return {
        "answer": summary,
        "citations": citations,
        "confidence": "medium",
        "needs_clarification": tax_year is None,
        "status": validation["status"],
    }

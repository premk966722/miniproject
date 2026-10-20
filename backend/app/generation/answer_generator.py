from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.evidence.citation_manager import CitationRecord


class AnswerStatus(str, Enum):
    ANSWERED = "answered"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    GENERATION_ERROR = "generation_error"


@dataclass
class AnswerResponse:
    answer_id: str
    question: str
    status: AnswerStatus
    answer_text: str
    tax_period: Optional[str]
    assumptions: List[str] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    clarification_question: Optional[str] = None
    evidence_sufficient: bool = False
    applicability_status: str = "supported"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer_id": self.answer_id,
            "question": self.question,
            "status": self.status.value,
            "answer_text": self.answer_text,
            "tax_period": self.tax_period,
            "assumptions": self.assumptions,
            "citations": self.citations,
            "supporting_evidence": self.supporting_evidence,
            "limitations": self.limitations,
            "clarification_question": self.clarification_question,
            "evidence_sufficient": self.evidence_sufficient,
            "applicability_status": self.applicability_status,
        }


class AnswerGenerator:
    def generate(
        self,
        question: str,
        tax_period: Optional[str],
        evidence: List[Dict[str, Any]],
        citations: Optional[List[CitationRecord]] = None,
        assumptions: Optional[List[str]] = None,
        limitations: Optional[List[str]] = None,
        conflicting_evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> AnswerResponse:
        if conflicting_evidence:
            return AnswerResponse(
                answer_id=str(uuid4()),
                question=question,
                status=AnswerStatus.CONFLICTING_EVIDENCE,
                answer_text="Retrieved materials disagree or have unresolved applicability for this period. The system will not choose between them without a verified legal version.",
                tax_period=tax_period,
                assumptions=assumptions or [],
                citations=[],
                supporting_evidence=[],
                limitations=(limitations or []) + ["Conflicting or potentially superseded passages were found; verify the governing version before relying on an answer."],
                clarification_question="Can you confirm the assessment year and the applicable version of the provision?",
                evidence_sufficient=False,
                applicability_status="conflicting",
            )
        if not evidence:
            if tax_period:
                answer_text = (
                    f"The indexed official-source evidence does not contain a verified passage that answers this question for {tax_period}. "
                    "No tax conclusion or citation can be provided from the available corpus."
                )
                clarification_question = None
                default_limitations = [
                    f"No applicable, period-verified passage was found for {tax_period}.",
                    "The registered source corpus is limited; add or select a vetted official document before relying on an answer.",
                ]
            else:
                answer_text = (
                    "The available evidence is insufficient to answer this question reliably. "
                    "Please specify the relevant assessment year or financial year."
                )
                clarification_question = "Which tax year or assessment year should the answer be interpreted for?"
                default_limitations = ["No suitable evidence was found and the applicable tax period is unresolved."]
            return AnswerResponse(
                answer_id=str(uuid4()),
                question=question,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                answer_text=answer_text,
                tax_period=tax_period,
                assumptions=assumptions or ([f"Requested period: {tax_period}."] if tax_period else ["No tax-period-specific evidence was selected."]),
                citations=[],
                supporting_evidence=[],
                limitations=limitations or default_limitations,
                clarification_question=clarification_question,
                evidence_sufficient=False,
                applicability_status="unresolved",
            )

        selected = evidence[:3]
        citation_rows = []
        for citation in citations or []:
            citation_rows.append(citation.to_dict() if isinstance(citation, CitationRecord) else citation)

        if not citation_rows:
            for hit in selected:
                source = hit.get("metadata") or hit
                citation_rows.append({
                    "citation_id": str(uuid4()),
                    "document_id": source.get("document_id") or hit.get("document_id"),
                    "chunk_id": source.get("chunk_id") or hit.get("chunk_id"),
                    "document_title": source.get("document_title") or hit.get("document_title"),
                    "issuing_authority": source.get("issuing_authority") or hit.get("issuing_authority"),
                    "url": source.get("source_url") or hit.get("source_url"),
                    "section_identifier": source.get("section_number") or hit.get("section_number") or "General guidance",
                    "supporting_passage": (source.get("text") or hit.get("text"))[:300],
                    "source_version": source.get("source_version") or hit.get("source_version"),
                    "applicable_period": (
                        source.get("applicable_assessment_year")
                        or source.get("applicable_tax_year")
                        or hit.get("applicable_assessment_year")
                        or hit.get("applicable_tax_year")
                    ),
                    "provenance_status": "verified",
                })

        answer_summary = self._summarize_evidence(question, tax_period, selected)

        return AnswerResponse(
            answer_id=str(uuid4()),
            question=question,
            status=AnswerStatus.ANSWERED,
            answer_text=answer_summary,
            tax_period=tax_period,
            assumptions=assumptions or ["Evidence was selected only from official or verified sources."],
            citations=citation_rows,
            supporting_evidence=selected,
            limitations=limitations or ["The answer is limited to the selected evidence and does not claim broader legal certainty beyond the cited passages."],
            evidence_sufficient=True,
            applicability_status="supported",
        )

    @staticmethod
    def _summarize_evidence(question: str, tax_period: Optional[str], evidence: List[Dict[str, Any]]) -> str:
        text = "\n".join(str(item.get("text") or "") for item in evidence)
        lower_question = question.lower()
        context = f" for AY {tax_period}" if tax_period else ""
        text_compact = re.sub(r"\s+", "", text.lower())

        if re.search(r"\b80c\b", lower_question) and "80c" in text.lower():
            quoted_limit = re.search(r"aggregate amount of deductions admissible.*?maximum limit of\s*([^.;\n]+)", text, re.IGNORECASE | re.DOTALL)
            if quoted_limit:
                return (
                    f"For the requested period{context}, the retrieved official FAQ discusses the combined limit for deductions under sections 80C, 80CCC and 80CCD(1) as {quoted_limit.group(1).strip()}. "
                    "This FAQ does not establish the full Section 80C eligibility rules or the taxpayer-specific amount; consult the cited governing provisions and conditions."
                )
            if (
                ("new tax regime" in lower_question or "new regime" in lower_question)
                and (
                    "deductionscannotbeclaimed" in text_compact
                    or "deductionsarenotallowed" in text_compact
                )
                and ("80ccd(2)/80cch/80jjaa" in text_compact or "80ccd(2)" in text_compact)
                and "oldtaxregime" in text_compact
            ):
                return (
                    f"For AY {tax_period}, the Income Tax Department FAQ states that the new tax regime is the default and Chapter VIA deductions are not allowed under it, except sections 80CCD(2), 80CCH and 80JJAA. "
                    "The FAQ says taxpayers seeking other applicable Chapter VIA deductions must opt for the old regime using the relevant ITR option. It does not specify a Section 80C deduction amount."
                )

        return (
            "The retrieved official-source passages are relevant to the question, but the available corpus does not provide enough verified detail for a specific conclusion. "
            "Review the cited passages and governing provision; no further legal rule has been inferred."
        )

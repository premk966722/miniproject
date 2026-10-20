from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


YEAR_PATTERN = re.compile(r"(?:AY|assessment year|tax year|FY|financial year)\s*(20\d{2}-\d{2}|20\d{2}/\d{2}|20\d{2})", re.IGNORECASE)
YEAR_ONLY_PATTERN = re.compile(r"\b(20\d{2}-\d{2}|20\d{2}/\d{2}|20\d{2})\b")


@dataclass
class YearResolution:
    requested_text: str
    tax_period: Optional[str] = None
    period_type: str = "unknown"
    resolution_status: str = "resolved"
    requires_clarification: bool = False
    supporting_evidence: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class YearResolver:
    def resolve(self, question: str) -> YearResolution:
        normalized = (question or "").strip()
        if not normalized:
            return YearResolution(
                requested_text="",
                period_type="unknown",
                resolution_status="unresolved",
                requires_clarification=True,
                notes=["No tax period was supplied."],
            )

        match = YEAR_PATTERN.search(normalized)
        if match:
            raw = match.group(1).replace("/", "-")
            period = raw
            lower = normalized.lower()
            if "assessment year" in lower or "ay" in lower:
                period_type = "assessment_year"
            elif "financial year" in lower or "fy" in lower:
                period_type = "financial_year"
            else:
                period_type = "tax_year"
            return YearResolution(
                requested_text=normalized,
                tax_period=period,
                period_type=period_type,
                resolution_status="resolved",
                requires_clarification=False,
                supporting_evidence=[raw],
                notes=[f"Resolved explicit period {period} from the question."],
            )

        year_match = YEAR_ONLY_PATTERN.search(normalized)
        if year_match:
            raw = year_match.group(1).replace("/", "-")
            return YearResolution(
                requested_text=normalized,
                tax_period=raw,
                period_type="tax_year",
                resolution_status="resolved",
                requires_clarification=False,
                supporting_evidence=[raw],
                notes=[f"Resolved a standalone year reference {raw} from the question."],
            )

        if "year" in normalized.lower():
            return YearResolution(
                requested_text=normalized,
                period_type="unknown",
                resolution_status="needs_clarification",
                requires_clarification=True,
                notes=["The question refers to a tax year but does not specify a period clearly enough to answer safely."],
            )

        return YearResolution(
            requested_text=normalized,
            period_type="unknown",
            resolution_status="unresolved",
            requires_clarification=True,
            notes=["No explicit tax period could be resolved from the question."],
        )

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.ingestion.source_registry import ALLOWED_DOMAINS


class ApplicabilityStatus(str, Enum):
    SUPPORTED = "supported"
    NOT_APPLICABLE = "not_applicable"
    UNRESOLVED = "unresolved"
    POTENTIALLY_SUPERSEDED = "potentially_superseded"
    CONFLICTING = "conflicting"


@dataclass
class ApplicabilityResult:
    status: ApplicabilityStatus
    reasons: List[str] = field(default_factory=list)
    authority_verified: bool = False
    period_established: bool = False
    metadata_complete: bool = False
    source_url: Optional[str] = None
    source_version: Optional[str] = None


class ApplicabilityValidator:
    def validate(self, hit: Dict[str, Any], requested_period: Optional[str] = None) -> ApplicabilityResult:
        if not hit:
            return ApplicabilityResult( status=ApplicabilityStatus.UNRESOLVED, reasons=["No evidence object was supplied."] )

        url = hit.get("source_url") or hit.get("url") or ""
        has_url = bool(url)
        domain_ok = False
        if has_url:
            host = url.split("//")[-1].split("/")[0].lower()
            domain_ok = host in ALLOWED_DOMAINS or any(host.endswith(f".{domain}") for domain in ALLOWED_DOMAINS)

        authority_ok = bool(hit.get("issuing_authority") or hit.get("authority"))
        metadata_complete = bool(hit.get("text"))

        effective_to = hit.get("effective_to")
        applicable_year = hit.get("applicable_assessment_year") or hit.get("applicable_tax_year")
        if not has_url or not domain_ok:
            return ApplicabilityResult(
                status=ApplicabilityStatus.UNRESOLVED,
                reasons=["The source provenance could not be verified from the supplied metadata."],
                authority_verified=authority_ok,
                period_established=bool(applicable_year),
                metadata_complete=metadata_complete,
                source_url=url,
                source_version=hit.get("source_version"),
            )
        if not authority_ok and not hit.get("document_type"):
            return ApplicabilityResult(
                status=ApplicabilityStatus.UNRESOLVED,
                reasons=["The authority behind the passage is not sufficiently documented."],
                authority_verified=False,
                period_established=bool(applicable_year),
                metadata_complete=metadata_complete,
                source_url=url,
                source_version=hit.get("source_version"),
            )
        if requested_period and applicable_year and str(applicable_year) != str(requested_period):
            return ApplicabilityResult(
                status=ApplicabilityStatus.NOT_APPLICABLE,
                reasons=[f"The passage is tagged to {applicable_year}, not the requested period {requested_period}."],
                authority_verified=authority_ok,
                period_established=True,
                metadata_complete=metadata_complete,
                source_url=url,
                source_version=hit.get("source_version"),
            )
        if requested_period and not applicable_year:
            return ApplicabilityResult(
                status=ApplicabilityStatus.UNRESOLVED,
                reasons=["The passage has no tax-period applicability metadata for the requested period."],
                authority_verified=authority_ok,
                period_established=False,
                metadata_complete=metadata_complete,
                source_url=url,
                source_version=hit.get("source_version"),
            )
        if effective_to and not requested_period:
            return ApplicabilityResult(
                status=ApplicabilityStatus.POTENTIALLY_SUPERSEDED,
                reasons=["The passage has an explicit end date; its applicability needs a specific requested period."],
                authority_verified=authority_ok,
                period_established=bool(applicable_year),
                metadata_complete=metadata_complete,
                source_url=url,
                source_version=hit.get("source_version"),
            )

        return ApplicabilityResult(
            status=ApplicabilityStatus.SUPPORTED,
            reasons=["The source is official and the available metadata is consistent with the passage."],
            authority_verified=authority_ok,
            period_established=bool(applicable_year or requested_period),
            metadata_complete=metadata_complete,
            source_url=url,
            source_version=hit.get("source_version"),
        )

from __future__ import annotations

from app.evidence.citation_manager import CitationManager
from app.evidence.evidence_selector import EvidenceSelector
from app.generation.answer_generator import AnswerGenerator, AnswerResponse, AnswerStatus
from app.tax.applicability_validator import ApplicabilityStatus, ApplicabilityValidator
from app.tax.year_resolver import YearResolver


SAMPLE_HITS = [
    {
        "chunk_id": "c-1",
        "document_id": "d-1",
        "document_title": "Section 80C deduction",
        "source_url": "https://www.incometax.gov.in/",
        "issuing_authority": "Income Tax Department",
        "document_type": "official",
        "act_name": "Income-tax Act, 1961",
        "section_number": "80C",
        "subsection_number": None,
        "rule_number": None,
        "publication_date": "2024-01-01",
        "effective_from": "2024-04-01",
        "effective_to": None,
        "applicable_assessment_year": "2025-26",
        "applicable_tax_year": "2025-26",
        "source_version": "v1",
        "content_hash": "hash-1",
        "authority_level": "official",
        "ingestion_timestamp": "2024-01-01T00:00:00Z",
        "text": "Section 80C allows deduction for eligible investments subject to limits and conditions.",
    },
    {
        "chunk_id": "c-2",
        "document_id": "d-2",
        "document_title": "Old regime note",
        "source_url": "https://www.incometax.gov.in/",
        "issuing_authority": "Income Tax Department",
        "document_type": "guidance",
        "act_name": "official guidance",
        "section_number": None,
        "subsection_number": None,
        "rule_number": None,
        "publication_date": "2024-01-01",
        "effective_from": "2024-04-01",
        "effective_to": None,
        "applicable_assessment_year": "2025-26",
        "applicable_tax_year": "2025-26",
        "source_version": "v2",
        "content_hash": "hash-2",
        "authority_level": "official",
        "ingestion_timestamp": "2024-01-01T00:00:00Z",
        "text": "The old regime may still apply where the taxpayer is eligible and the relevant provisions are followed.",
    },
    {
        "chunk_id": "c-3",
        "document_id": "d-3",
        "document_title": "Superseded rule",
        "source_url": "https://www.incometax.gov.in/",
        "issuing_authority": "Income Tax Department",
        "document_type": "official",
        "act_name": "Income-tax Act, 1961",
        "section_number": "80C",
        "subsection_number": None,
        "rule_number": None,
        "publication_date": "2022-01-01",
        "effective_from": "2021-04-01",
        "effective_to": "2024-03-31",
        "applicable_assessment_year": "2024-25",
        "applicable_tax_year": "2024-25",
        "source_version": "v0",
        "content_hash": "hash-3",
        "authority_level": "official",
        "ingestion_timestamp": "2022-01-01T00:00:00Z",
        "text": "This historical provision applied only until 31 March 2024 and is not the current rule for later years.",
    },
]


def test_year_resolution_prefers_explicit_assessment_year() -> None:
    resolver = YearResolver()
    result = resolver.resolve("What is the deduction under AY 2025-26?")
    assert result.tax_period == "2025-26"
    assert result.period_type == "assessment_year"
    assert result.requires_clarification is False


def test_year_resolution_flags_ambiguous_period() -> None:
    resolver = YearResolver()
    result = resolver.resolve("What changed for the tax year?")
    assert result.requires_clarification is True
    assert result.resolution_status in {"unresolved", "needs_clarification"}


def test_applicability_validator_marks_superseded_and_supported() -> None:
    validator = ApplicabilityValidator()
    result = validator.validate(SAMPLE_HITS[0])
    assert result.status == ApplicabilityStatus.SUPPORTED
    superseded = validator.validate(SAMPLE_HITS[2])
    assert superseded.status == ApplicabilityStatus.POTENTIALLY_SUPERSEDED


def test_evidence_selector_keeps_direct_support_and_removes_duplicates() -> None:
    selector = EvidenceSelector()
    result = selector.select(
        question="What is the deduction under section 80C for AY 2025-26?",
        tax_period="2025-26",
        candidate_hits=SAMPLE_HITS,
    )
    assert result["can_answer"] is True
    assert any(item["chunk_id"] == "c-1" for item in result["supporting_evidence"])
    assert all(item["chunk_id"] != "c-3" for item in result["supporting_evidence"])


def test_citation_manager_validates_urls_and_ids() -> None:
    manager = CitationManager()
    evidence = SAMPLE_HITS[0]
    created = manager.create_citation(evidence)
    assert created.citation_id
    assert created.url == evidence["source_url"]
    assert manager.validate_citation(created) is True


def test_citation_manager_rejects_passage_tampering() -> None:
    manager = CitationManager()
    evidence = SAMPLE_HITS[0]
    citation = manager.create_citation(evidence)
    citation.supporting_passage = "A fabricated passage not present in the chunk."
    assert manager.validate_citation(citation, evidence) is False


def test_answer_generator_returns_grounded_response() -> None:
    generator = AnswerGenerator()
    evidence = SAMPLE_HITS[:2]
    response = generator.generate(
        question="What is the deduction under section 80C for AY 2025-26?",
        tax_period="2025-26",
        evidence=evidence,
        citations=[CitationManager().create_citation(hit) for hit in evidence],
    )
    assert isinstance(response, AnswerResponse)
    assert response.status == AnswerStatus.ANSWERED
    assert response.evidence_sufficient is True
    assert len(response.citations) >= 1


def test_answer_generator_abstains_on_conflicting_evidence() -> None:
    response = AnswerGenerator().generate(
        question="What rule applies?",
        tax_period="2025-26",
        evidence=SAMPLE_HITS[:1],
        conflicting_evidence=[SAMPLE_HITS[2]],
    )
    assert response.status == AnswerStatus.CONFLICTING_EVIDENCE
    assert response.evidence_sufficient is False
    assert response.citations == []


def test_insufficient_evidence_does_not_ask_again_for_known_period() -> None:
    response = AnswerGenerator().generate(
        question="What is the applicable rule?",
        tax_period="2024-25",
        evidence=[],
    )
    assert response.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert response.tax_period == "2024-25"
    assert response.clarification_question is None
    assert "for 2024-25" in response.answer_text
    assert response.citations == []


def test_insufficient_evidence_requests_missing_period() -> None:
    response = AnswerGenerator().generate(
        question="What is the applicable rule?",
        tax_period=None,
        evidence=[],
    )
    assert response.clarification_question == "Which tax year or assessment year should the answer be interpreted for?"


def test_answer_summarizes_only_supported_regime_deduction_claim() -> None:
    official_faq_excerpt = (
        "COMMON ITR ISSUES AND FAQ'S FOR FILING RETURN FOR AY 2024-25. "
        "From AY 2024-25, new tax regime has become the default tax regime and VIA deductions cannot be claimed, "
        "except deduction u/s 80CCD(2)/80CCH/80JJAA as per the provision of Section 115BAC of the Income Tax Act, 1961. "
        "In case taxpayer wants to claim any other VIA deductions, then taxpayer need to choose for old tax regime."
    )
    evidence = [{**SAMPLE_HITS[0], "text": official_faq_excerpt, "applicable_assessment_year": "2024-25"}]
    response = AnswerGenerator().generate(
        question="Can I claim section 80C under the new tax regime for AY 2024-25?",
        tax_period="2024-25",
        evidence=evidence,
        citations=[CitationManager().create_citation(evidence[0])],
    )
    assert response.status == AnswerStatus.ANSWERED
    assert "80CCD(2), 80CCH and 80JJAA" in response.answer_text
    assert "does not specify a Section 80C deduction amount" in response.answer_text


def test_answer_summary_matches_extracted_pdf_line_wrapping() -> None:
    excerpt = (
        "Q.8: Taxpayer unable to claim all other deductions other than 80CCD (2)?\n"
        "Ans: From AY 2024-25, new tax regime has become the default tax regime where claiming of chapter\n"
        "VIA deductions are not allowed except section 80CCD (2) as per the provision of section 115BAC.\n"
        "In case taxpayer wants to claim any other VIA deductions, then taxpayer must choose ‘Old Tax Regime’."
    )
    evidence = [{**SAMPLE_HITS[0], "text": excerpt, "applicable_assessment_year": "2024-25"}]
    response = AnswerGenerator().generate(
        question="Can I claim section 80C under the new tax regime for AY 2024-25?",
        tax_period="2024-25",
        evidence=evidence,
        citations=[CitationManager().create_citation(evidence[0])],
    )
    assert "new tax regime is the default" in response.answer_text
    assert "does not specify a Section 80C deduction amount" in response.answer_text


def test_requested_period_requires_explicit_applicability_metadata() -> None:
    hit = {**SAMPLE_HITS[0], "applicable_tax_year": None, "applicable_assessment_year": None}
    result = ApplicabilityValidator().validate(hit, requested_period="2025-26")
    assert result.status == ApplicabilityStatus.UNRESOLVED


def test_assessment_year_metadata_matches_requested_period() -> None:
    hit = {**SAMPLE_HITS[0], "applicable_tax_year": None, "applicable_assessment_year": "2025-26"}
    result = ApplicabilityValidator().validate(hit, requested_period="2025-26")
    assert result.status == ApplicabilityStatus.SUPPORTED


def test_api_chat_citation_is_linked_to_retrieved_evidence(monkeypatch) -> None:
    from app import main
    from fastapi.testclient import TestClient

    evidence = {**SAMPLE_HITS[0], "applicable_tax_year": "2025-26"}
    monkeypatch.setattr(main.retriever, "search", lambda *args, **kwargs: [evidence])
    response = TestClient(main.app).post("/api/v1/chat", json={
        "question": "What does section 80C address for AY 2025-26?",
        "tax_year": "2025-26",
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    citation = payload["citations"][0]
    assert citation["document_id"] == evidence["document_id"]
    assert citation["chunk_id"] == evidence["chunk_id"]
    assert evidence["text"].startswith(citation["supporting_passage"])


def test_api_chat_with_selected_period_abstains_without_reasking_for_year(monkeypatch) -> None:
    from app import main
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main.retriever, "search", lambda *args, **kwargs: [])
    response = TestClient(main.app).post("/api/v1/chat", json={
        "question": "What should I verify before choosing a regime?",
        "tax_year": "2024-25",
        "regime": "new",
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_evidence"
    assert payload["tax_period"] == "2024-25"
    assert payload["clarification_question"] is None
    assert payload["citations"] == []
    assert "for 2024-25" in payload["answer"]

from __future__ import annotations

import secrets
import threading
import time
import uuid
from collections import deque
from typing import Deque

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional

from app.config import ADMIN_API_KEY, CORS_ORIGINS, MAX_REQUEST_BYTES, RATE_LIMIT_PER_MINUTE
from app.db import create_conversation, get_conversation, init_db, list_index_documents, list_sources, save_feedback, save_message
from app.ingestion.ingestion_report import build_ingestion_report
from app.ingestion.ingestion_service import ingest_registered_sources
from app.ingestion.source_registry import ensure_default_sources
from app.generation.answer import generate_answer
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.query_analyzer import analyze_query
from app.tax.year_resolver import YearResolver
from app.evidence.evidence_selector import EvidenceSelector
from app.evidence.citation_manager import CitationManager
from app.generation.answer_generator import AnswerGenerator

app = FastAPI(title="TAX-SHIELD", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

_retrieval_lock = threading.RLock()


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [".".join(str(part) for part in error.get("loc", ())) for error in exc.errors()]
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_request", "message": "Request validation failed.", "fields": fields}})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "The request could not be completed."}})

_rate_windows: Dict[str, Deque[float]] = {}
_rate_lock = threading.Lock()


@app.middleware("http")
async def request_limits(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            too_large = int(content_length) > MAX_REQUEST_BYTES
        except ValueError:
            return JSONResponse(status_code=400, content={"error": {"code": "invalid_content_length", "message": "Invalid Content-Length header."}})
        if too_large:
            return JSONResponse(status_code=413, content={"error": {"code": "request_too_large", "message": "Request body exceeds the configured size limit."}})

    if request.url.path.startswith("/api/"):
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with _rate_lock:
            if client not in _rate_windows and len(_rate_windows) >= 10000:
                for address, timestamps in list(_rate_windows.items()):
                    while timestamps and now - timestamps[0] >= 60:
                        timestamps.popleft()
                    if not timestamps:
                        _rate_windows.pop(address, None)
                if len(_rate_windows) >= 10000:
                    return JSONResponse(status_code=429, headers={"Retry-After": "60"}, content={"error": {"code": "rate_limited", "message": "Request rate limit exceeded."}})
            window = _rate_windows.setdefault(client, deque())
            while window and now - window[0] >= 60:
                window.popleft()
            if len(window) >= RATE_LIMIT_PER_MINUTE:
                return JSONResponse(status_code=429, headers={"Retry-After": "60"}, content={"error": {"code": "rate_limited", "message": "Request rate limit exceeded."}})
            window.append(now)
    return await call_next(request)


def require_admin_key(supplied_key: Optional[str]) -> None:
    if not ADMIN_API_KEY or not supplied_key or not secrets.compare_digest(supplied_key, ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail={"code": "admin_auth_required", "message": "Valid administrative credentials are required."})

init_db()
ensure_default_sources()
retriever = HybridRetriever()
retriever.index_documents(list_index_documents())
_ingestion_lock = threading.Lock()
resolver = YearResolver()
selector = EvidenceSelector()
citation_manager = CitationManager()
answer_generator = AnswerGenerator()


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(..., min_length=3, max_length=12000)
    tax_year: Optional[str] = Field(default=None, pattern=r"^20\d{2}[-/]\d{2}$", max_length=7)
    regime: Optional[str] = Field(default=None, pattern=r"^(old|new)$")
    conversation_id: Optional[str] = Field(default=None, min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$")


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str = Field(..., min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    question: str = Field(..., min_length=3, max_length=12000)
    helpful: bool


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "tax-shield", "version": "0.1.0"}


@app.get("/api/v1/sources")
def get_sources() -> Dict[str, Any]:
    return {"sources": list_sources()}


@app.post("/api/v1/chat")
def chat(request: ChatRequest) -> Dict[str, Any]:
    conversation_id = request.conversation_id
    if conversation_id:
        if not get_conversation(conversation_id):
            raise HTTPException(status_code=404, detail={"code": "conversation_not_found", "message": "Conversation not found."})
    else:
        conversation_id = "conv-" + uuid.uuid4().hex
        create_conversation(conversation_id, request.question[:60])
    save_message(conversation_id, "msg-" + uuid.uuid4().hex, "user", request.question)

    period_resolution = resolver.resolve(request.question)
    if (
        request.tax_year
        and period_resolution.tax_period
        and request.tax_year.replace("/", "-") != period_resolution.tax_period.replace("/", "-")
    ):
        answer_text = "The selected tax period conflicts with the period stated in the question. Please choose one period before proceeding."
        save_message(conversation_id, "msg-" + uuid.uuid4().hex, "assistant", answer_text)
        return {
            "conversation_id": conversation_id,
            "status": "needs_clarification",
            "answer": answer_text,
            "tax_period": None,
            "citations": [],
            "supporting_evidence": [],
            "limitations": ["The question and selected tax period disagree; neither was silently preferred."],
            "clarification_question": "Should I use the tax period in your question or the selected period?",
            "evidence_sufficient": False,
        }
    selected_tax_period = request.tax_year or period_resolution.tax_period
    if request.tax_year is None and period_resolution.requires_clarification:
        fallback = generate_answer(request.question, [], tax_year=selected_tax_period, regime=request.regime)
        save_message(conversation_id, "msg-" + uuid.uuid4().hex, "assistant", fallback["answer"])
        return {
            "conversation_id": conversation_id,
            "status": "needs_clarification",
            "answer": fallback["answer"],
            "tax_period": selected_tax_period,
            "citations": [],
            "supporting_evidence": [],
            "limitations": ["The system could not safely resolve the tax period from the question."],
            "clarification_question": "Which assessment year or tax year should the answer apply to?",
            "evidence_sufficient": False,
        }

    with _retrieval_lock:
        query_period = analyze_query(request.question)
        if request.tax_year:
            retrieval_hits = retriever.search(request.question, tax_year=request.tax_year)
        elif query_period.get("assessment_year"):
            retrieval_hits = retriever.search(
                request.question,
                assessment_year=query_period["assessment_year"],
            )
        else:
            retrieval_hits = retriever.search(request.question, tax_year=selected_tax_period)
        hits = retrieval_hits
    selected = selector.select(request.question, selected_tax_period, hits)
    evidence = selected["supporting_evidence"]
    if selected["conflicting_evidence"]:
        evidence = []
    citations = []
    for item in selected["supporting_evidence"]:
        citation = citation_manager.create_citation(item["metadata"])
        if citation_manager.validate_citation(citation, item["metadata"]):
            citations.append(citation)
    if selected["supporting_evidence"] and len(citations) != len(selected["supporting_evidence"]):
        evidence = []
    result = answer_generator.generate(
        question=request.question,
        tax_period=selected_tax_period,
        evidence=[item["metadata"] for item in evidence],
        citations=citations,
        assumptions=[f"Resolved period: {selected_tax_period}"] if selected_tax_period else ["No explicit tax period was supplied."],
        limitations=(
            [f"No applicable, period-verified passage was found for {selected_tax_period}."]
            if selected_tax_period and not evidence
            else ["No suitable period-verified evidence was found in the current corpus."]
            if not evidence
            else []
        ),
        conflicting_evidence=selected["conflicting_evidence"],
    )
    save_message(conversation_id, "msg-" + uuid.uuid4().hex, "assistant", result.answer_text)
    public = result.to_dict()
    public["conversation_id"] = conversation_id
    public["answer"] = public.pop("answer_text")
    public["status"] = public["status"]
    return public


@app.post("/api/v1/admin/index/rebuild")
def rebuild_index(x_admin_key: Optional[str] = Header(default=None, alias="x-admin-key")) -> Dict[str, Any]:
    require_admin_key(x_admin_key)
    if not _ingestion_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail={"code": "ingestion_in_progress", "message": "Cannot rebuild the retrieval index while ingestion is in progress."})
    with _retrieval_lock:
        try:
            documents = list_index_documents()
            retriever.index_documents(documents)
        finally:
            _ingestion_lock.release()
    return {"status": "rebuilt", "indexed_chunks": len(documents)}


@app.post("/api/v1/feedback")
def feedback(request: FeedbackRequest) -> Dict[str, Any]:
    if not get_conversation(request.conversation_id):
        raise HTTPException(status_code=404, detail={"code": "conversation_not_found", "message": "Conversation not found."})
    feedback_id = "fb-" + uuid.uuid4().hex
    save_feedback(feedback_id, request.conversation_id, request.question, 1 if request.helpful else 0)
    return {"status": "recorded"}


@app.get("/api/v1/conversations")
def conversations() -> Dict[str, Any]:
    raise HTTPException(status_code=404, detail={"code": "disabled", "message": "Conversation enumeration is disabled to prevent disclosure of private records."})


@app.get("/api/v1/conversations/{conversation_id}")
def conversation_detail(conversation_id: str) -> Dict[str, Any]:
    raise HTTPException(status_code=404, detail={"code": "disabled", "message": "Conversation history retrieval is disabled until user authentication and authorization are configured."})


@app.get("/api/v1/admin/ingestion/status")
def ingestion_status(x_admin_key: Optional[str] = Header(default=None, alias="x-admin-key")) -> Dict[str, Any]:
    require_admin_key(x_admin_key)
    return {"status": "ok", "sources": list_sources()}


@app.post("/api/v1/admin/ingestion/sync")
def ingestion_sync(x_admin_key: Optional[str] = Header(default=None, alias="x-admin-key")) -> Dict[str, Any]:
    require_admin_key(x_admin_key)
    if not _ingestion_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail={"code": "ingestion_in_progress", "message": "An ingestion sync is already running."})
    try:
        report = ingest_registered_sources()
        with _retrieval_lock:
            retriever.index_documents(list_index_documents())
    finally:
        _ingestion_lock.release()
    return {"status": "completed", **build_ingestion_report(report["results"]) }


@app.get("/openapi.json")
def openapi_json() -> Dict[str, Any]:
    return app.openapi()

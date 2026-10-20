from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.ingestion import source_fetcher
from app.ingestion.source_registry import is_allowed_url


def test_allowlist_rejects_http_credentials_and_nonstandard_ports() -> None:
    assert is_allowed_url("https://www.incometax.gov.in/")
    assert not is_allowed_url("http://www.incometax.gov.in/")
    assert not is_allowed_url("https://user@www.incometax.gov.in/")
    assert not is_allowed_url("https://www.incometax.gov.in:8443/")
    assert not is_allowed_url("https://incometax.gov.in.example.org/")


def test_fetch_rejects_redirects_outside_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        url="https://www.incometax.gov.in/",
        is_redirect=True,
        is_permanent_redirect=False,
        headers={"Location": "http://127.0.0.1/admin"},
        close=lambda: None,
    )
    session = SimpleNamespace(get=lambda *args, **kwargs: response)
    monkeypatch.setattr(source_fetcher, "_assert_public_destination", lambda url: None)
    monkeypatch.setattr(source_fetcher, "_build_session", lambda: session)

    with pytest.raises(ValueError, match="redirected outside"):
        source_fetcher.fetch_url("https://www.incometax.gov.in/")


def test_fetch_rejects_private_dns_destinations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        source_fetcher.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.8", 443))],
    )
    with pytest.raises(ValueError, match="non-public"):
        source_fetcher._assert_public_destination("https://www.incometax.gov.in/")


def test_fetch_stream_enforces_response_size(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        url = "https://www.incometax.gov.in/"
        status_code = 200
        is_redirect = False
        is_permanent_redirect = False
        headers = {"Content-Type": "text/html"}

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int):
            yield b"1234"
            yield b"5678"

        def close(self) -> None:
            return None

    monkeypatch.setattr(source_fetcher, "_assert_public_destination", lambda url: None)
    monkeypatch.setattr(source_fetcher, "_build_session", lambda: SimpleNamespace(get=lambda *args, **kwargs: Response()))
    with pytest.raises(ValueError, match="size limit"):
        source_fetcher.fetch_url("https://www.incometax.gov.in/", max_bytes=5)


def test_api_validation_admin_auth_and_private_history(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main
    from app.main import app

    client = TestClient(app)
    invalid_chat = client.post("/api/v1/chat", json={"question": "ok", "unexpected": "no"})
    assert invalid_chat.status_code == 422
    assert invalid_chat.json()["error"]["code"] == "invalid_request"

    period_conflict = client.post("/api/v1/chat", json={
        "question": "What applies for AY 2025-26?",
        "tax_year": "2024-25",
    })
    assert period_conflict.status_code == 200
    assert period_conflict.json()["status"] == "needs_clarification"
    assert period_conflict.json()["citations"] == []

    official_evidence = {
        "chunk_id": "ay-chunk",
        "document_id": "ay-doc",
        "document_title": "AY source excerpt",
        "source_url": "https://www.incometax.gov.in/",
        "issuing_authority": "Income Tax Department",
        "document_type": "official",
        "text": "Section 80C is a provision of the Income-tax Act.",
        "applicable_tax_year": None,
        "applicable_assessment_year": "2025-26",
    }
    monkeypatch.setattr(main.retriever, "search", lambda *args, **kwargs: [official_evidence])
    ay_chat = client.post("/api/v1/chat", json={
        "question": "What is addressed by section 80C for AY 2025-26?",
    })
    assert ay_chat.status_code == 200
    assert ay_chat.json()["status"] == "answered"
    assert ay_chat.json()["tax_period"] == "2025-26"

    admin_status = client.get("/api/v1/admin/ingestion/status")
    assert admin_status.status_code == 403
    rebuild_status = client.post("/api/v1/admin/index/rebuild")
    assert rebuild_status.status_code == 403

    conversation_list = client.get("/api/v1/conversations")
    assert conversation_list.status_code == 404
    conversation_detail = client.get("/api/v1/conversations/conv-0123456789abcdef0123456789abcdef")
    assert conversation_detail.status_code == 404


def test_rate_limit_and_cors_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main
    from fastapi.testclient import TestClient

    main._rate_windows.clear()
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 1)
    client = TestClient(main.app)
    assert client.get("/api/v1/sources").status_code == 200
    assert client.get("/api/v1/sources").status_code == 429
    main._rate_windows.clear()

    preflight = client.options(
        "/api/v1/sources",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"

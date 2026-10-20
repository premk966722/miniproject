from __future__ import annotations

import hashlib
import ipaddress
import socket
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.ingestion.source_registry import is_allowed_url

DEFAULT_HEADERS = {
    "User-Agent": "TAX-SHIELD/0.1 research-bot (official-source ingestion)",
    "Accept": "text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
}
MAX_RESPONSE_BYTES = 10 * 1024 * 1024


def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods={"GET"},
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _assert_public_destination(url: str) -> None:
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError("The source URL has no hostname.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError("The approved source hostname could not be resolved.") from exc
    if not addresses:
        raise ValueError("The source hostname did not resolve to an address.")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("The source hostname resolves to a non-public network address.")


def fetch_url(
    url: str,
    timeout: int = 20,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> Dict[str, Any]:
    if not is_allowed_url(url):
        raise ValueError("URL is not on the approved official-source allowlist.")

    headers = dict(DEFAULT_HEADERS)
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    session = _build_session()
    request_url = url
    response = None
    for redirect_count in range(4):
        _assert_public_destination(request_url)
        response = session.get(request_url, headers=headers, timeout=(5, timeout), allow_redirects=False, stream=True)
        if not (response.is_redirect or response.is_permanent_redirect):
            break
        location = response.headers.get("Location")
        response.close()
        if not location or redirect_count == 3:
            raise ValueError("The official source returned an invalid or excessive redirect chain.")
        request_url = urljoin(request_url, location)
        if not is_allowed_url(request_url):
            raise ValueError("The official source redirected outside the approved domain list.")
    if response is None:
        raise ValueError("The official source request did not produce a response.")
    final_url = response.url
    if not is_allowed_url(final_url):
        response.close()
        raise ValueError("The fetched URL is outside the approved domain list.")

    if response.status_code == 304:
        response.close()
        return {
            "status": "not_modified",
            "url": final_url,
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }

    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    declared_length = response.headers.get("Content-Length")
    if declared_length and int(declared_length) > max_bytes:
        response.close()
        raise ValueError("The response exceeds the configured size limit.")
    chunks = []
    total = 0
    try:
        for part in response.iter_content(chunk_size=64 * 1024):
            total += len(part)
            if total > max_bytes:
                raise ValueError("The response exceeds the configured size limit.")
            chunks.append(part)
    finally:
        response.close()
    payload = b"".join(chunks)
    if not payload:
        raise ValueError("empty response received")

    allowed_content_types = ("text/html", "application/xhtml+xml", "application/pdf", "application/octet-stream", "application/xml")
    if not any(token in content_type.lower() for token in allowed_content_types) and not url.lower().endswith((".pdf", ".html", ".htm")):
        raise ValueError(f"unsupported content type received: {content_type or 'unknown'}")

    return {
        "status": "ok",
        "url": final_url,
        "content_type": content_type,
        "body": payload,
        "headers": dict(response.headers),
        "etag": response.headers.get("ETag"),
        "last_modified": response.headers.get("Last-Modified"),
        "content_hash": hashlib.sha256(payload).hexdigest(),
    }

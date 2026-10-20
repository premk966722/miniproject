from __future__ import annotations

from typing import Any, Dict

import requests

from app.ingestion.source_registry import is_allowed_url

DEFAULT_HEADERS = {
    "User-Agent": "TAX-SHIELD/0.1 (research bot; contact: research@example.com)",
    "Accept": "text/html,application/pdf,application/xhtml+xml",
}


def fetch_url(url: str, timeout: int = 20) -> Dict[str, Any]:
    if not is_allowed_url(url):
        raise ValueError(f"URL is not in the approved official-source allowlist: {url}")
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
    final_url = response.url
    if not is_allowed_url(final_url):
        raise ValueError(f"redirected URL is outside the approved domain set: {final_url}")
    response.raise_for_status()
    return {
        "final_url": final_url,
        "status_code": response.status_code,
        "content_type": response.headers.get("Content-Type", ""),
        "body": response.content,
        "headers": dict(response.headers),
    }

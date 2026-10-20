from __future__ import annotations

import re
from typing import List


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"[\t\r]+", " ", text).replace("\u00a0", " ")


def _remove_repeated_headers(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    filtered: List[str] = []
    for line in lines:
        if not line:
            continue
        if re.match(r"^(HEADER|FOOTER|Home|Income Tax Department|Ministry of Finance|Government of India|Privacy Policy|Contact Us|Skip to main content|Page \d+)$", line, flags=re.IGNORECASE):
            continue
        if filtered and filtered[-1].lower() == line.lower():
            continue
        filtered.append(line)
    return "\n".join(filtered)


def clean_extracted_text(text: str) -> str:
    if not text:
        return ""
    normalized = _normalize_whitespace(text)
    normalized = normalized.replace("\n ", "\n")
    normalized = _remove_repeated_headers(normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"\s+\n", "\n", normalized)
    normalized = re.sub(r"\n\s+", "\n", normalized)
    normalized = re.sub(r"\n{2,}", "\n\n", normalized)
    normalized = re.sub(r"\s{2,}", " ", normalized)
    return normalized.strip()

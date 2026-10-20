from __future__ import annotations

import hashlib
from typing import Optional


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def detect_document_change(previous_hash: Optional[str], current_hash: Optional[str]) -> bool:
    if previous_hash is None and current_hash is not None:
        return True
    if previous_hash is None or current_hash is None:
        return False
    return previous_hash != current_hash

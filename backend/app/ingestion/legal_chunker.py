from __future__ import annotations

import re
from typing import List

SECTION_PATTERN = re.compile(r"(?im)(?:^|\n)\s*(Section|Rule|Schedule|Notification|Circular|Circular No\.|Notification No\.)\s+[A-Za-z0-9.\-/()]+")


def chunk_legal_text(text: str, max_chars: int = 1800) -> List[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    sections = re.split(r"(?=(?:^|\n)\s*(?:Section|Rule|Schedule|Notification|Circular|Circular No\.|Notification No\.)\s+[A-Za-z0-9.\-/()]+)", cleaned, flags=re.IGNORECASE)
    chunks: List[str] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= max_chars:
            chunks.append(section)
        else:
            sub_chunks = [section[i:i + max_chars] for i in range(0, len(section), max_chars)]
            chunks.extend(sub_chunk.strip() for sub_chunk in sub_chunks if sub_chunk.strip())
    return chunks

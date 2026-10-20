from __future__ import annotations

import re
from typing import Dict, Tuple

import fitz
from bs4 import BeautifulSoup


def extract_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag_name in ["script", "style", "noscript", "svg", "iframe"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    article = soup.select_one("article, main, .content, .page, .entry-content, #content") or soup
    lines: list[str] = []

    for heading in article.select("h1, h2, h3, h4, h5"):
        text = heading.get_text(" ", strip=True)
        if text:
            lines.append(text)

    for block in article.select("p, li, td, th, div"):
        text = block.get_text(" ", strip=True)
        if text and len(text) > 2:
            lines.append(text)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_pdf_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[str] = []
    try:
        for page in doc:
            text = page.get_text("text")
            if text and text.strip():
                pages.append(text)
    finally:
        doc.close()
    return "\n".join(pages).strip()


def extract_document_text(url: str, content_type: str, payload: bytes) -> Tuple[str, str]:
    normalized = (content_type or "").lower()
    if "pdf" in normalized or url.lower().endswith(".pdf"):
        text = extract_pdf_text(payload)
        return text, "PDF document"

    text = extract_html_text(payload.decode("utf-8", errors="replace"))
    return text, "HTML webpage"


def extract_document_metadata(url: str, html: str | None = None) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    soup = BeautifulSoup(html or "", "html.parser") if html else None
    if soup:
        title = soup.title.get_text(" ", strip=True) if soup.title else None
        if title:
            metadata["title"] = title
    metadata["source_url"] = url
    return metadata

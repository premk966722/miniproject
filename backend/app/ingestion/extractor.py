from __future__ import annotations

from typing import Dict, List

import fitz
from bs4 import BeautifulSoup


def extract_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    headings = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = tag.get_text(" ", strip=True)
        if text:
            headings.append(text)
    body_lines = [p.get_text(" ", strip=True) for p in soup.find_all(["p", "li", "td", "th"]) if p.get_text(" ", strip=True)]
    combined = "\n".join(headings + body_lines)
    return "\n".join(line for line in combined.splitlines() if line.strip())


def extract_pdf_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text:
            pages.append(text)
    doc.close()
    return "\n".join(pages)


def extract_document_bytes(content_type: str, payload: bytes) -> str:
    if "pdf" in content_type.lower():
        return extract_pdf_text(payload)
    return extract_html_text(payload.decode("utf-8", errors="replace"))


def extract_document_html(html: str) -> Dict[str, str]:
    text = extract_html_text(html)
    return {"text": text, "title": "Official Government Source"}

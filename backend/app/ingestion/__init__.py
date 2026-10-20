"""Official-source ingestion package for TAX-SHIELD."""

from app.ingestion.document_cleaner import clean_extracted_text
from app.ingestion.document_extractor import extract_document_text, extract_html_text, extract_pdf_text
from app.ingestion.document_versioning import compute_content_hash, detect_document_change
from app.ingestion.ingestion_report import build_ingestion_report
from app.ingestion.ingestion_service import ingest_registered_sources, ingest_source_document
from app.ingestion.legal_chunker import chunk_legal_text
from app.ingestion.source_fetcher import fetch_url
from app.ingestion.source_registry import ALLOWED_DOMAINS, ensure_default_sources, is_allowed_url

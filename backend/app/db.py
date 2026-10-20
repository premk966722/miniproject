from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                official_domain TEXT,
                source_url TEXT,
                source_category TEXT,
                issuing_authority TEXT,
                document_type TEXT,
                ingestion_status TEXT,
                last_successful_fetch TEXT,
                last_attempted_fetch TEXT,
                content_hash TEXT,
                publication_date TEXT,
                source_version TEXT,
                error_info TEXT,
                enabled INTEGER DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                source_id TEXT,
                title TEXT,
                source_url TEXT,
                document_type TEXT,
                content_hash TEXT,
                publication_date TEXT,
                raw_path TEXT,
                processed_path TEXT,
                created_at TEXT,
                metadata TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT,
                content TEXT,
                metadata TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at TEXT,
                updated_at TEXT,
                title TEXT,
                summary TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                conversation_id TEXT,
                question TEXT,
                helpful INTEGER,
                created_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def insert_source(source: Dict[str, Any]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO sources (
                source_id, official_domain, source_url, source_category, issuing_authority,
                document_type, ingestion_status, last_successful_fetch, last_attempted_fetch,
                content_hash, publication_date, source_version, error_info, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source.get("source_id"),
                source.get("official_domain"),
                source.get("source_url"),
                source.get("source_category"),
                source.get("issuing_authority"),
                source.get("document_type"),
                source.get("ingestion_status", "not_started"),
                source.get("last_successful_fetch"),
                source.get("last_attempted_fetch"),
                source.get("content_hash"),
                source.get("publication_date"),
                source.get("source_version"),
                source.get("error_info"),
                int(bool(source.get("enabled", True))),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_sources() -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM sources ORDER BY source_id").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_conversation(conversation_id: str, title: str = "New Question") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO conversations (conversation_id, created_at, updated_at, title, summary) VALUES (?, datetime('now'), datetime('now'), ?, ?)",
            (conversation_id, title, ""),
        )
        conn.commit()
    finally:
        conn.close()


def save_message(conversation_id: str, message_id: str, role: str, content: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO messages (message_id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (message_id, conversation_id, role, content),
        )
        conn.commit()
    finally:
        conn.close()


def list_conversations() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_feedback(feedback_id: str, conversation_id: str, question: str, helpful: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO feedback (feedback_id, conversation_id, question, helpful, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (feedback_id, conversation_id, question, helpful),
        )
        conn.commit()
    finally:
        conn.close()


def store_document(document_id: str, source_id: str, title: str, source_url: str, document_type: str, content_hash: str, publication_date: Optional[str], raw_path: str, processed_path: str, metadata: Dict[str, Any]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO documents (document_id, source_id, title, source_url, document_type, content_hash, publication_date, raw_path, processed_path, created_at, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)",
            (document_id, source_id, title, source_url, document_type, content_hash, publication_date, raw_path, processed_path, json.dumps(metadata)),
        )
        conn.commit()
    finally:
        conn.close()


def insert_chunk(chunk_id: str, document_id: str, content: str, metadata: Dict[str, Any]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO chunks (chunk_id, document_id, content, metadata, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (chunk_id, document_id, content, json.dumps(metadata)),
        )
        conn.commit()
    finally:
        conn.close()


def list_index_documents() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT c.chunk_id, c.document_id, c.content, c.metadata, d.title,
                      d.source_url, d.document_type
               FROM chunks c JOIN documents d ON d.document_id = c.document_id
               ORDER BY c.created_at, c.chunk_id"""
        ).fetchall()
        documents: List[Dict[str, Any]] = []
        for row in rows:
            metadata = json.loads(row["metadata"] or "{}")
            documents.append({
                **metadata,
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "text": row["content"],
                "document_title": row["title"],
                "source_url": row["source_url"],
                "document_type": row["document_type"],
                "metadata": metadata,
            })
        return documents
    finally:
        conn.close()

"""SQLite database service for document versions and chat history."""
import aiosqlite
import os
import uuid
from datetime import datetime
from typing import Optional, List

DB_PATH = os.environ.get("LOOMIN_DB_PATH", "data/loomin.db")


async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Create tables if they don't exist."""
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                size_bytes INTEGER DEFAULT 0,
                uploaded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                embedding_index INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                citations TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS editor_versions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                word_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)
        await db.commit()
    finally:
        await db.close()


# ─── Document Operations ────────────────────────────────────────────
async def insert_document(doc_id: str, filename: str, file_type: str,
                          content: str, chunk_count: int, size_bytes: int):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO documents (id, filename, file_type, content, chunk_count, size_bytes, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (doc_id, filename, file_type, content, chunk_count, size_bytes,
             datetime.utcnow().isoformat())
        )
        await db.commit()
    finally:
        await db.close()


async def insert_chunks(chunks: List[dict]):
    db = await get_db()
    try:
        await db.executemany(
            "INSERT INTO document_chunks (id, document_id, content, chunk_index, embedding_index) "
            "VALUES (?, ?, ?, ?, ?)",
            [(c["id"], c["document_id"], c["content"], c["chunk_index"], c["embedding_index"])
             for c in chunks]
        )
        await db.commit()
    finally:
        await db.close()


async def list_documents() -> List[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, filename, file_type, chunk_count, size_bytes, uploaded_at FROM documents ORDER BY uploaded_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def delete_document(doc_id: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await db.execute("DELETE FROM document_chunks WHERE document_id = ?", (doc_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def get_chunks_by_document(doc_id: str) -> List[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, content, chunk_index, embedding_index FROM document_chunks WHERE document_id = ? ORDER BY chunk_index",
            (doc_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_all_chunks() -> List[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT dc.id, dc.content, dc.chunk_index, dc.embedding_index, dc.document_id, d.filename "
            "FROM document_chunks dc JOIN documents d ON dc.document_id = d.id "
            "ORDER BY dc.embedding_index"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


# ─── Chat History ────────────────────────────────────────────────────
async def insert_chat_message(role: str, content: str, model: str = None,
                              citations: str = None, metadata: str = None):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO chat_history (id, role, content, model, citations, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), role, content, model, citations, metadata,
             datetime.utcnow().isoformat())
        )
        await db.commit()
    finally:
        await db.close()


async def get_chat_history(limit: int = 50) -> List[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM chat_history ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        await db.close()


# ─── Editor Versions ────────────────────────────────────────────────
async def save_editor_version(title: str, content: str) -> str:
    doc_id = str(uuid.uuid4())
    word_count = len(content.split())
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO editor_versions (id, title, content, word_count, created_at) VALUES (?, ?, ?, ?, ?)",
            (doc_id, title, content, word_count, datetime.utcnow().isoformat())
        )
        await db.commit()
    finally:
        await db.close()
    return doc_id


async def list_editor_versions() -> List[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, word_count, created_at FROM editor_versions ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_editor_version(version_id: str) -> Optional[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM editor_versions WHERE id = ?", (version_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()

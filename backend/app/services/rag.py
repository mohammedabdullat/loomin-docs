"""RAG pipeline service — FAISS vector indexing and retrieval with citations."""
import os
import uuid
import time
import faiss
import numpy as np
from typing import List, Optional, Tuple
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services import database as db

# ─── Configuration ──────────────────────────────────────────────────
EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
)
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TOP_K = 5

# ─── Module State ───────────────────────────────────────────────────
_model: Optional[SentenceTransformer] = None
_index: Optional[faiss.IndexFlatL2] = None
_chunk_map: List[dict] = []  # Parallel list: index_position → chunk metadata

FAISS_INDEX_PATH = "data/faiss.index"
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def get_index() -> faiss.IndexFlatL2:
    global _index
    if _index is None:
        if os.path.exists(FAISS_INDEX_PATH):
            _index = faiss.read_index(FAISS_INDEX_PATH)
        else:
            _index = faiss.IndexFlatL2(EMBEDDING_DIM)
    return _index


def save_index():
    os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
    faiss.write_index(get_index(), FAISS_INDEX_PATH)


# ─── Text Extraction ───────────────────────────────────────────────
def extract_text_from_pdf(file_bytes: bytes) -> str:
    from PyPDF2 import PdfReader
    import io
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text(filename: str, file_bytes: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    # .md, .txt, and other text files
    return file_bytes.decode("utf-8", errors="replace")


# ─── Chunking ──────────────────────────────────────────────────────
def chunk_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


# ─── Indexing ──────────────────────────────────────────────────────
async def index_document(filename: str, file_bytes: bytes) -> dict:
    """
    Extract text from a file, chunk it, embed it, and add to FAISS index.
    Returns document info dict.
    """
    global _chunk_map

    text = extract_text(filename, file_bytes)
    chunks = chunk_text(text)

    if not chunks:
        raise ValueError("No text content could be extracted from the file.")

    # Generate embeddings
    model = get_model()
    embeddings = model.encode(chunks, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")

    # Add to FAISS
    index = get_index()
    start_idx = index.ntotal
    index.add(embeddings)
    save_index()

    # Store in DB
    doc_id = str(uuid.uuid4())
    ext = filename.rsplit(".", 1)[-1].lower()

    await db.insert_document(
        doc_id=doc_id,
        filename=filename,
        file_type=ext,
        content=text,
        chunk_count=len(chunks),
        size_bytes=len(file_bytes),
    )

    chunk_records = []
    for i, chunk in enumerate(chunks):
        chunk_record = {
            "id": str(uuid.uuid4()),
            "document_id": doc_id,
            "content": chunk,
            "chunk_index": i,
            "embedding_index": start_idx + i,
        }
        chunk_records.append(chunk_record)
        _chunk_map.append({
            "chunk_id": chunk_record["id"],
            "document_id": doc_id,
            "document_name": filename,
            "content": chunk,
        })

    await db.insert_chunks(chunk_records)

    return {
        "id": doc_id,
        "filename": filename,
        "file_type": ext,
        "chunk_count": len(chunks),
        "size_bytes": len(file_bytes),
    }


# ─── Retrieval ─────────────────────────────────────────────────────
def retrieve(query: str, top_k: int = TOP_K) -> Tuple[List[dict], float]:
    """
    Retrieve the most relevant chunks for a query.
    Returns (citations, retrieval_time_ms).
    """
    start = time.perf_counter()

    index = get_index()
    if index.ntotal == 0:
        return [], 0.0

    model = get_model()
    query_embedding = model.encode([query], show_progress_bar=False)
    query_embedding = np.array(query_embedding, dtype="float32")

    distances, indices = index.search(query_embedding, min(top_k, index.ntotal))

    citations = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(_chunk_map):
            continue
        chunk_info = _chunk_map[idx]
        citations.append({
            "chunk_id": chunk_info["chunk_id"],
            "document_name": chunk_info["document_name"],
            "content": chunk_info["content"],
            "score": float(1.0 / (1.0 + dist)),  # Convert L2 distance to similarity
        })

    retrieval_time = (time.perf_counter() - start) * 1000
    return citations, retrieval_time


async def rebuild_chunk_map():
    """Rebuild the in-memory chunk map from the database."""
    global _chunk_map
    chunks = await db.get_all_chunks()
    _chunk_map = [
        {
            "chunk_id": c["id"],
            "document_id": c["document_id"],
            "document_name": c["filename"],
            "content": c["content"],
        }
        for c in chunks
    ]


async def remove_document_from_index(doc_id: str):
    """
    Remove a document and rebuild the FAISS index.
    FAISS doesn't support deletion, so we rebuild from scratch.
    """
    global _index, _chunk_map

    await db.delete_document(doc_id)

    # Rebuild index from remaining chunks
    all_chunks = await db.get_all_chunks()
    _chunk_map = []

    _index = faiss.IndexFlatL2(EMBEDDING_DIM)

    if all_chunks:
        model = get_model()
        texts = [c["content"] for c in all_chunks]
        embeddings = model.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype="float32")
        _index.add(embeddings)

        for i, c in enumerate(all_chunks):
            _chunk_map.append({
                "chunk_id": c["id"],
                "document_id": c["document_id"],
                "document_name": c["filename"],
                "content": c["content"],
            })

    save_index()

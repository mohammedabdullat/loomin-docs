"""Pydantic models for request/response schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


# ─── Chat ───────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    model: str = "llama3"
    selected_text: Optional[str] = None
    action: Optional[str] = None  # "summarize" | "improve" | None
    document_content: Optional[str] = None


class Citation(BaseModel):
    chunk_id: str
    document_name: str
    content: str
    score: float


class LatencyMetadata(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    retrieval_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    tokens_generated: int = 0
    tokens_per_sec: float = 0.0
    total_time_ms: float = 0.0


class ChatResponse(BaseModel):
    response: str
    citations: List[Citation] = []
    metadata: LatencyMetadata = Field(default_factory=LatencyMetadata)


# ─── Documents ──────────────────────────────────────────────────────
class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: str
    size_bytes: int = 0


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]


# ─── Editor ─────────────────────────────────────────────────────────
class EditorSaveRequest(BaseModel):
    content: str
    title: str = "Untitled"


class EditorVersion(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    word_count: int


class EditorVersionListResponse(BaseModel):
    versions: List[EditorVersion]


# ─── Models ─────────────────────────────────────────────────────────
class OllamaModel(BaseModel):
    name: str
    size: Optional[str] = None
    parameter_size: Optional[str] = None
    context_length: int = 4096


class ModelListResponse(BaseModel):
    models: List[OllamaModel]


# ─── Token Estimation ──────────────────────────────────────────────
class TokenEstimateRequest(BaseModel):
    document_content: str = ""
    retrieved_chunks: List[str] = []
    model: str = "llama3"


class TokenEstimateResponse(BaseModel):
    document_tokens: int
    chunk_tokens: int
    total_tokens: int
    context_limit: int
    usage_percent: float

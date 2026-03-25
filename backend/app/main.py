"""Loomin-Docs Backend — FastAPI Application."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.database import init_db
from app.services.rag import rebuild_chunk_map
from app.routes import chat, documents, editor, models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and rebuild FAISS chunk map on startup."""
    await init_db()
    await rebuild_chunk_map()
    yield


app = FastAPI(
    title="Loomin-Docs API",
    description="Air-gapped collaborative editor with RAG-powered AI assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://frontend:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(editor.router)
app.include_router(models.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "loomin-docs-backend"}

"""Document upload, listing, and deletion routes."""
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models import DocumentInfo, DocumentListResponse
from app.services import rag

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {"pdf", "md", "txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...)):
    # Validate extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 50 MB.")

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")

    # Index the document
    try:
        doc_info = await rag.index_document(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing error: {str(e)}")

    return DocumentInfo(
        id=doc_info["id"],
        filename=doc_info["filename"],
        file_type=doc_info["file_type"],
        chunk_count=doc_info["chunk_count"],
        uploaded_at="just now",
        size_bytes=doc_info["size_bytes"],
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    from app.services import database as db
    docs = await db.list_documents()
    return DocumentListResponse(
        documents=[
            DocumentInfo(
                id=d["id"],
                filename=d["filename"],
                file_type=d["file_type"],
                chunk_count=d["chunk_count"],
                uploaded_at=d["uploaded_at"],
                size_bytes=d.get("size_bytes", 0),
            )
            for d in docs
        ]
    )


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    try:
        await rag.remove_document_from_index(doc_id)
        return {"status": "deleted", "id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

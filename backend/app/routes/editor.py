"""Editor versioning routes."""
from fastapi import APIRouter, HTTPException
from app.models import EditorSaveRequest, EditorVersion, EditorVersionListResponse
from app.services import database as db

router = APIRouter(prefix="/api/editor", tags=["editor"])


@router.post("/save", response_model=EditorVersion)
async def save_version(req: EditorSaveRequest):
    version_id = await db.save_editor_version(req.title, req.content)
    version = await db.get_editor_version(version_id)
    if not version:
        raise HTTPException(status_code=500, detail="Failed to save version.")

    return EditorVersion(
        id=version["id"],
        title=version["title"],
        content=version["content"],
        created_at=version["created_at"],
        word_count=version["word_count"],
    )


@router.get("/versions", response_model=EditorVersionListResponse)
async def list_versions():
    versions = await db.list_editor_versions()
    return EditorVersionListResponse(
        versions=[
            EditorVersion(
                id=v["id"],
                title=v["title"],
                content="",  # Don't send content in list view
                created_at=v["created_at"],
                word_count=v["word_count"],
            )
            for v in versions
        ]
    )


@router.get("/versions/{version_id}", response_model=EditorVersion)
async def get_version(version_id: str):
    version = await db.get_editor_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found.")

    return EditorVersion(
        id=version["id"],
        title=version["title"],
        content=version["content"],
        created_at=version["created_at"],
        word_count=version["word_count"],
    )

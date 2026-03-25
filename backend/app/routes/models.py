"""Model listing and token estimation routes."""
from fastapi import APIRouter
from app.models import ModelListResponse, OllamaModel, TokenEstimateRequest, TokenEstimateResponse
from app.services import ollama

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    models = await ollama.list_models()
    return ModelListResponse(
        models=[
            OllamaModel(
                name=m["name"],
                size=str(m.get("size", "")),
                parameter_size=m.get("parameter_size", ""),
                context_length=m.get("context_length", 4096),
            )
            for m in models
        ]
    )


@router.post("/tokens/estimate", response_model=TokenEstimateResponse)
async def estimate_tokens(req: TokenEstimateRequest):
    doc_tokens = ollama.estimate_tokens(req.document_content)
    chunk_tokens = sum(ollama.estimate_tokens(c) for c in req.retrieved_chunks)
    total = doc_tokens + chunk_tokens
    context_limit = ollama.estimate_context_length(req.model)
    usage_pct = min(100.0, (total / context_limit) * 100) if context_limit > 0 else 0

    return TokenEstimateResponse(
        document_tokens=doc_tokens,
        chunk_tokens=chunk_tokens,
        total_tokens=total,
        context_limit=context_limit,
        usage_percent=round(usage_pct, 1),
    )

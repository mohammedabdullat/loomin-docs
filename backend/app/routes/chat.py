"""Chat route — RAG-powered AI assistant with latency tracing."""
import time
import uuid
import json
from fastapi import APIRouter, HTTPException
from app.models import ChatRequest, ChatResponse, Citation, LatencyMetadata
from app.services import rag, ollama, pii, database as db

router = APIRouter(prefix="/api", tags=["chat"])

SYSTEM_PROMPT = """You are Loomin, an AI writing assistant embedded in a collaborative document editor.
Your job is to help users write, edit, and improve their documents.

RULES:
- When provided with context from uploaded files, ONLY use information from those files.
- Always cite your sources by referring to the document name.
- If you cannot answer from the provided context, say so clearly.
- Be concise, helpful, and precise.
- When asked to summarize, be thorough but concise.
- When asked to improve text, maintain the original meaning while enhancing clarity and style."""


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    request_id = str(uuid.uuid4())
    total_start = time.perf_counter()

    # Build the prompt based on action type
    if req.action == "summarize" and req.selected_text:
        user_prompt = f"Please summarize the following text concisely:\n\n{req.selected_text}"
    elif req.action == "improve" and req.selected_text:
        user_prompt = f"Please improve the following text for clarity, grammar, and style. Return ONLY the improved text:\n\n{req.selected_text}"
    else:
        user_prompt = req.message

    # PII sanitization
    sanitized_prompt = pii.sanitize_for_llm(user_prompt)

    # RAG retrieval
    citations_data, retrieval_time_ms = rag.retrieve(sanitized_prompt)

    # Build context block
    context_block = ""
    if citations_data:
        context_parts = []
        for i, c in enumerate(citations_data):
            context_parts.append(f"[Source {i+1}: {c['document_name']}]\n{c['content']}")
        context_block = "\n\n---\nRelevant context from uploaded documents:\n" + "\n\n".join(context_parts) + "\n---\n"

    # Include document content if provided
    doc_context = ""
    if req.document_content:
        # Truncate to avoid overwhelming the context
        doc_text = req.document_content[:4000]
        doc_context = f"\n\nCurrent document content:\n{doc_text}\n"

    full_prompt = f"{context_block}{doc_context}\nUser request: {sanitized_prompt}"

    # Generate response via Ollama
    gen_start = time.perf_counter()
    try:
        result = await ollama.generate(
            prompt=full_prompt,
            model=req.model,
            system=SYSTEM_PROMPT,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {str(e)}")

    gen_time_ms = (time.perf_counter() - gen_start) * 1000
    total_time_ms = (time.perf_counter() - total_start) * 1000

    # Calculate tokens per second
    eval_count = result.get("eval_count", 0)
    eval_duration_ns = result.get("eval_duration", 1)
    tokens_per_sec = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0

    # Build response
    citations = [
        Citation(
            chunk_id=c["chunk_id"],
            document_name=c["document_name"],
            content=c["content"][:200],
            score=c["score"],
        )
        for c in citations_data
    ]

    metadata = LatencyMetadata(
        request_id=request_id,
        retrieval_time_ms=round(retrieval_time_ms, 2),
        generation_time_ms=round(gen_time_ms, 2),
        tokens_generated=eval_count,
        tokens_per_sec=round(tokens_per_sec, 2),
        total_time_ms=round(total_time_ms, 2),
    )

    response_text = result["response"]

    # Persist chat history
    await db.insert_chat_message("user", req.message, req.model)
    await db.insert_chat_message(
        "assistant", response_text, req.model,
        citations=json.dumps([c.model_dump() for c in citations]),
        metadata=json.dumps(metadata.model_dump()),
    )

    return ChatResponse(
        response=response_text,
        citations=citations,
        metadata=metadata,
    )


@router.get("/chat/history")
async def get_history():
    history = await db.get_chat_history()
    return {"messages": history}

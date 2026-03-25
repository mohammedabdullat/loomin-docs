"""Ollama HTTP API wrapper for local LLM inference."""
import httpx
import json
import time
import os
from typing import AsyncGenerator, Optional

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# Default context lengths per model family
MODEL_CONTEXT_LENGTHS = {
    "llama3": 8192,
    "llama2": 4096,
    "mistral": 8192,
    "mixtral": 32768,
    "phi": 4096,
    "gemma": 8192,
    "qwen": 32768,
    "codellama": 16384,
}


def estimate_context_length(model_name: str) -> int:
    """Estimate context window size based on model name."""
    name_lower = model_name.lower()
    for key, length in MODEL_CONTEXT_LENGTHS.items():
        if key in name_lower:
            return length
    return 4096  # conservative default


async def list_models() -> list:
    """Get available models from Ollama."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                details = m.get("details", {})
                models.append({
                    "name": name,
                    "size": m.get("size", ""),
                    "parameter_size": details.get("parameter_size", ""),
                    "context_length": estimate_context_length(name),
                })
            return models
        except Exception:
            return []


async def generate(
    prompt: str,
    model: str = "llama3",
    system: str = None,
    stream: bool = False,
    temperature: float = 0.7,
) -> dict:
    """
    Generate a completion from Ollama (non-streaming).
    Returns dict with keys: response, total_duration, eval_count, eval_duration
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return {
            "response": data.get("response", ""),
            "total_duration": data.get("total_duration", 0),
            "eval_count": data.get("eval_count", 0),
            "eval_duration": data.get("eval_duration", 0),
        }


async def generate_stream(
    prompt: str,
    model: str = "llama3",
    system: str = None,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """Stream tokens from Ollama."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload) as resp:
            async for line in resp.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            return
                    except json.JSONDecodeError:
                        continue


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return max(1, len(text) // 4)

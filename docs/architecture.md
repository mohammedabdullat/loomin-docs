# Architecture — Loomin-Docs

## System Overview

```mermaid
graph TD
    subgraph "Frontend Container (port 3000)"
        A[React + TipTap Editor] -->|User types/selects text| B[AI Sidebar Panel]
        B -->|Chat / Summarize / Improve| C[API Client]
        B -->|Upload files| C
        B -->|Model selector| C
        D[Token Visualization] -->|Estimates usage| C
    end

    subgraph "Backend Container (port 8000)"
        C -->|HTTP REST| E[FastAPI Server]
        E --> F[PII Sanitizer]
        F --> G[RAG Pipeline]
        G --> H[FAISS Index]
        G --> I[Sentence-Transformers<br/>all-MiniLM-L6-v2]
        E --> J[SQLite DB]
        J --> J1[Documents & Chunks]
        J --> J2[Chat History]
        J --> J3[Editor Versions]
    end

    subgraph "Ollama Container (port 11434)"
        F -->|Sanitized prompt +<br/>retrieved context| K[Ollama API]
        K --> L[Llama 3 / Mistral<br/>GGUF Weights]
    end

    style A fill:#7c5cfc,color:#fff
    style K fill:#5c8afc,color:#fff
    style H fill:#5cfcb6,color:#000
```

## Data Flow — Chat with RAG

```mermaid
sequenceDiagram
    participant User
    participant Editor
    participant Sidebar
    participant Backend
    participant FAISS
    participant Ollama

    User->>Editor: Types/selects text
    User->>Sidebar: Sends message or clicks "Summarize"
    Sidebar->>Backend: POST /api/chat (message, selected_text, model)
    Backend->>Backend: PII Sanitization
    Backend->>FAISS: Retrieve top-K similar chunks
    FAISS-->>Backend: Citations with scores
    Backend->>Ollama: Generate (prompt + context + system)
    Ollama-->>Backend: Response + eval metrics
    Backend->>Backend: Compute latency metadata
    Backend-->>Sidebar: {response, citations[], metadata{}}
    Sidebar-->>User: Render markdown + citations + metrics
```

## Data Flow — File Upload & Indexing

```mermaid
sequenceDiagram
    participant User
    participant FilesPanel
    participant Backend
    participant TextExtractor
    participant Chunker
    participant Embedder
    participant FAISS
    participant SQLite

    User->>FilesPanel: Drag & drop .pdf/.md/.txt
    FilesPanel->>Backend: POST /api/documents/upload (multipart)
    Backend->>TextExtractor: Extract text from file
    TextExtractor-->>Backend: Raw text
    Backend->>Chunker: Split (512 tokens, 50 overlap)
    Chunker-->>Backend: Text chunks[]
    Backend->>Embedder: Encode chunks (all-MiniLM-L6-v2)
    Embedder-->>Backend: Embedding vectors
    Backend->>FAISS: Add vectors to index
    Backend->>SQLite: Store document + chunks metadata
    Backend-->>FilesPanel: DocumentInfo
    FilesPanel-->>User: Show file in list
```

## Container Architecture

| Service | Image | Port | Volume |
|---------|-------|------|--------|
| Frontend | `loomin-frontend` (nginx) | 3000 | — |
| Backend | `loomin-backend` (Python 3.11) | 8000 | `backend-data` (SQLite + FAISS) |
| Ollama | `ollama/ollama` | 11434 | `ollama-models` (GGUF weights) |

All three containers share the `loomin-net` bridge network. The frontend nginx proxies `/api/*` to the backend.

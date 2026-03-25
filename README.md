# Loomin-Docs

> A real-time collaborative text editor with an AI assistant sidebar, powered by local LLMs via Ollama. Designed for air-gapped enterprise deployment on RHEL 9.

![Status](https://img.shields.io/badge/status-production--ready-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

## Features

- **Rich Text Editor** — TipTap-based editor with Markdown shortcuts and full formatting toolbar
- **AI Assistant Sidebar** — Chat with context-aware RAG, summarize/improve selected text
- **Multi-Model Support** — Switch between Ollama models (Llama 3, Mistral, etc.) via dropdown
- **RAG Pipeline** — Upload PDFs, Markdown, and text files; FAISS + sentence-transformers for retrieval with clickable citations
- **Token Visualization** — Real-time context window usage indicator
- **PII Sanitization** — Automatic masking of SSNs, emails, API keys before they reach the LLM
- **Latency Tracing** — Every response shows retrieval time, generation speed, and token count
- **Air-Gapped Deployment** — Full Docker Compose stack with offline bootstrap for RHEL 9

## Project Structure

```
loomin-docs/
├── frontend/          # React + TypeScript (Vite + TipTap)
├── backend/           # Python + FastAPI (RAG, Ollama, SQLite)
├── deploy/            # Docker Compose + RHEL 9 bootstrap
│   ├── docker-compose.yml
│   ├── setup.sh       # Air-gapped bootstrap script
│   ├── Modelfile      # Custom Ollama system prompt
│   └── README-DEPLOY.md
├── docs/              # Architecture diagrams (Mermaid)
├── verify/            # RAG faithfulness test
└── README.md
```

## Quick Start (Development)

### Prerequisites
- Node.js 20+
- Python 3.11+
- [Ollama](https://ollama.ai) installed and running

### 1. Start Ollama
```bash
ollama pull llama3
ollama serve
```

### 2. Start Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — the frontend proxies API calls to the backend at port 8000.

## Docker Deployment

```bash
cd deploy
docker compose up -d --build
```

Access at **http://localhost:3000**

## Air-Gapped RHEL 9 Deployment

See [deploy/README-DEPLOY.md](deploy/README-DEPLOY.md) for the complete offline bootstrap guide including:
- Docker RPM installation from local files
- Docker image sideloading from `.tar` archives
- Ollama model weight side-loading

```bash
# On the air-gapped VM:
sudo ./deploy/setup.sh
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message to AI with RAG retrieval |
| `/api/chat/history` | GET | Get chat history |
| `/api/documents/upload` | POST | Upload file for RAG indexing |
| `/api/documents` | GET | List uploaded documents |
| `/api/documents/{id}` | DELETE | Remove document and vectors |
| `/api/editor/save` | POST | Save document version |
| `/api/editor/versions` | GET | List document versions |
| `/api/models` | GET | List available Ollama models |
| `/api/tokens/estimate` | POST | Estimate token usage |
| `/api/health` | GET | Health check |

## Verification

```bash
# Run RAG faithfulness test (requires backend + Ollama running)
cd verify
python test_faithfulness.py --backend-url http://localhost:8000
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for Mermaid diagrams showing the full system data flow.

## License

MIT

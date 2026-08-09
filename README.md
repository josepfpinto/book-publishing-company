# Editorial AI — Book Publishing POC

An editorial AI assistant that lets publishing teams ask questions about *Little Women* and *Pride & Prejudice* using a RAG pipeline backed by Azure OpenAI and ChromaDB.

---

## What it does

- **Chat with a book** — ask questions; the assistant answers from retrieved passages and cites chapter and title
- **Compare books** — set scope to "Both Books" and the assistant draws on both collections in a single response
- **Streaming UI** — tokens stream progressively; source cards appear when the answer completes
- **Scope-aware history** — switching books mid-conversation doesn't bleed prior context into the new scope

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Docker Desktop | 4.x |
| Docker Compose | v2 (bundled with Docker Desktop) |
| Azure OpenAI resource | with `gpt-5.1-chat` and `text-embedding-3-large` deployments |

---

## First-time setup

```bash
# 1. Clone and enter the project
cd book-publishing-company

# 2. Copy and fill in credentials
cp .env.template .env
```

Edit `.env` and set all five values:

```
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=<chat-deployment-name>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<embedding-deployment-name>
```

---

## Running the app

```bash
# Build the backend image
docker compose build backend

# Ingest the books into ChromaDB (run once; safe to re-run)
docker compose run --rm backend python ingest.py

# Start backend + frontend
docker compose up
```

- **Backend API** → http://localhost:8000
- **Frontend UI** → http://localhost:3000

The frontend waits for the backend health check to pass before starting. No manual sequencing needed after `docker compose up`.

---

## Verifying the backend

```bash
# Health check
curl http://localhost:8000/api/health
# → {"status":"ok"}

# List ingested books
curl http://localhost:8000/api/books
# → [{"id":"little_women","title":"Little Women","chapter_count":47}, ...]

# Chat (streaming)
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"book_id":"little_women","message":"Who is Jo March?","history":[]}'
# → data: {"token":"Jo ..."}
# → data: {"token":"..."}
# → data: {"sources":[{"book_title":"Little Women","chapter_title":"Playing Pilgrims",...}]}
# → data: {"done":true}
```

Valid `book_id` values: `little_women` · `pride_prejudice` · `both`

---

## Running the test suite

```bash
# Offline tests — no Azure credentials needed
docker compose --profile test run --rm backend-test

# Or locally (Python 3.12 + dev deps installed)
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

The 7 errors in `test_ingestion.py` are expected when run outside Docker — those tests need the book HTML files that are only present inside the container.

---

## Project structure

```
book-publishing-company/
├── backend/
│   ├── core/               RAG logic (query analysis, retrieval, prompts, embeddings)
│   ├── api/
│   │   ├── deps.py         FastAPI lifespan — ChromaDB + AzureOpenAI singletons
│   │   └── routes/
│   │       ├── books.py    GET /api/books
│   │       └── chat.py     POST /api/chat  (SSE streaming)
│   ├── main.py             FastAPI app — CORS, lifespan, health check
│   ├── ingest.py           One-shot ingestion CLI (run before first `docker compose up`)
│   └── tests/              Offline test suite (80 tests, no live credentials needed)
├── frontend/               React + Vite chat UI (Phase 5)
├── books shared/           Source HTML books (COPY'd into Docker image at build time)
├── docker-compose.yml
├── .env.template           Copy to .env and fill in credentials
└── docs/
    ├── architecture.md     Code orientation — where things live and how they connect
    └── tasks/              Story scaffolding (plan + per-story design/tasks/tracker)
```

---

## Architecture overview

See [`docs/architecture.md`](docs/architecture.md) for the full data-flow diagram and decision log.

**Chat request lifecycle:**

```
POST /api/chat
  → analyze_query()      LLM decomposes message into 1–2 sub-queries with book targets
  → embed_texts()        Single Azure embedding call for all sub-queries
  → retrieve()           One ChromaDB query per sub-query, dedup by chunk ID
  → build_messages()     System prompt + scope-tagged history + retrieved passages
  → Azure chat stream    Tokens yielded as SSE frames
  → sources event        Top-3 citable chunk metadata
  → done event
```

---

## Known limitations (pre-production hardening)

These are deliberate POC trade-offs, not bugs:

| Limitation | Impact | Notes |
|---|---|---|
| Pre-LLM exceptions (network timeout during query analysis or embedding) produce HTTP 200 with no SSE frames | Client sees a blank/hung stream | Add a top-level `try/except` in `generate()` that yields `{"error":"..."}` + `{"done":true}` before Phase 6 go-live |
| Mid-stream Azure content filter raises after `.create()` succeeds | Partial token stream, then connection close, no `done` frame | Azure usually returns 400 at `.create()` time; mid-stream filter is rare but real |
| Model refusal (`delta.refusal`) produces an empty answer with no user-facing message | User sees blank response | Extend the streaming loop to check `delta.refusal` and emit an error event |

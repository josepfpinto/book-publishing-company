# Editorial AI — Book Publishing POC

An editorial AI assistant that lets publishing teams ask questions about *Little Women* and *Pride & Prejudice* using a RAG pipeline backed by Azure OpenAI and ChromaDB.

---

## What it does

- **Chat with a book** — ask questions; the assistant answers from retrieved passages and cites chapter and title
- **Compare books** — set scope to "Both Books" and the assistant draws on both collections in a single response
- **Streaming UI** — tokens stream progressively; source cards appear when the answer completes
- **Scope-aware history** — switching books mid-conversation doesn't bleed prior context into the new scope

---

## Approach

The assistant is built around **Retrieval-Augmented Generation (RAG)**: rather than relying on model memory for book content, it retrieves the most relevant passages at query time and grounds the LLM's answer in those passages. This produces verifiable, citable answers — an editor can check every source card against the physical text.

A user question travels through five stages:

1. **Query decomposition** — `analyze_query()` calls the LLM to convert the message into 1–2 targeted sub-queries, each with an explicit `book_id`. A comparative question ("How does Jo March differ from Elizabeth Bennet?") becomes two focused sub-queries, one per book.
2. **Embedding** — all sub-queries are embedded in a single batch call to `text-embedding-3-large`, producing dense vectors for semantic search.
3. **Retrieval** — ChromaDB returns the top-k chunks per sub-query, filtered by `book_id`; results are deduplicated by chunk ID and globally ranked by score.
4. **Prompting** — the top-5 chunks are included in the system prompt as numbered passages; the LLM is instructed to cite chapter and title when using any passage.
5. **Streaming** — `gpt-5.1-chat` streams tokens directly to the frontend over SSE; when generation ends, `select_citations()` picks the top-3 cited chunks to surface as source cards with chapter, title, and a short excerpt.

Books are parsed with chapter-aware chunking (~500 tokens, ~80-token overlap) so every chunk carries its chapter heading (e.g., "Chapter 9 — Meg Goes to Vanity Fair"). Citations are immediately verifiable rather than an anonymous reference.

Cross-book queries (scope set to "Both Books") remove the `book_id` filter entirely and retrieve from both collections in one pass, enabling genuine comparative questions across the two texts.

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

## Architecture

### Component flow

```
  Browser (React :3000)
       │
       │  POST /api/chat  →  SSE token stream
       ▼
  FastAPI (:8000)
       │
       ├─ analyze_query()   LLM decomposes message into 1–2 sub-queries
       ├─ embed_texts()     Single Azure embedding call for all sub-queries
       ├─ retrieve()        ChromaDB query per sub-query; dedup by chunk ID
       ├─ build_messages()  System prompt + scope-tagged history + passages
       │
       ├─────────────────────────────────────────────┐
       │                                             │
       ▼                                             ▼
  ChromaDB (named volume)                   Azure OpenAI
  books collection                          gpt-5.1-chat  (tokens → SSE)
  filtered by book_id                       text-embedding-3-large

  ingest.py (one-shot, run before first up)
       │
       ├─ parses little_women.html + pride_prejudice.html (COPY'd into image)
       ├─ chapter-aware chunking (~500 tokens, ~80-token overlap)
       ├─ embeds with text-embedding-3-large
       └─ writes to ChromaDB books collection
```

### Component table

| Component    | Role                                                              | Runs at          | Started by                                         |
|--------------|-------------------------------------------------------------------|------------------|----------------------------------------------------|
| React + Vite | Chat UI — book selector, message list, streaming output, sources  | Container `:3000`| `docker compose up`                                |
| FastAPI      | REST + SSE API, RAG orchestration                                 | Container `:8000`| `docker compose up`                                |
| ChromaDB     | Local vector store — 1 `books` collection, filtered by `book_id` | Named volume     | Auto-init on first run                             |
| `ingest.py`  | One-shot book parsing + embedding pipeline                        | Inside backend   | `docker compose run --rm backend python ingest.py` |
| Azure OpenAI | GPT-5.1-chat (answers) + text-embedding-3-large (vectors)        | External SaaS    | API key in `.env`                                  |

> Directory map, data flows, and code orientation: [`docs/architecture.md`](docs/architecture.md)

---

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| **Streaming transport** | FastAPI SSE via `fetch` + `ReadableStream` (not `EventSource`) | `EventSource` is GET-only — a chat endpoint must POST the message body. `fetch`+`ReadableStream` gives full request control at no extra complexity for the POC. |
| **Backend framework** | FastAPI (Python) | Async-native — SSE streaming requires `async def` generators; Flask/Django need workarounds. Also yields auto-generated OpenAPI docs as a bonus. |
| **Vector store** | ChromaDB in embedded (local) mode | Zero network overhead, zero ops — spins up inside the Docker image. One collection (`books`) with `book_id` metadata eliminates the need for a separate compare endpoint; cross-book queries run with no `where` filter. |
| **Chunking strategy** | Chapter-aware, ~500 tokens with ~80-token overlap | Preserves chapter metadata on every chunk so citations read "Chapter 9 — Meg Goes to Vanity Fair" rather than an anonymous ID. 500-token chunks improve retrieval precision and produce readable excerpts in source cards. |
| **Conversation scope tagging** | Book scope stored as a tag on each history message | Switching books mid-conversation must not bleed P&P context into a Little Women query. Scope-tagged history lets the backend filter out turns from a different book without discarding the session. |
| **Docker Compose infra** | Two services (backend `:8000`, frontend `:3000`) + named volume for ChromaDB | Self-contained — evaluator runs `docker compose up` with no external dependencies beyond Azure credentials. Health-check dependency ensures the frontend waits for the backend before starting. |

### Assumptions

| Assumption | Rationale |
|---|---|
| Fixed 2-book dataset — *Little Women* and *Pride & Prejudice* only | Books are `COPY`'d into the Docker image at build time; adding a title requires a rebuild and re-ingest |
| Source files are Project Gutenberg HTML with consistent DOM conventions | The BeautifulSoup parser targets `<h2>` elements for chapter breaks; a third book with different markup would require parser changes before it could be ingested |
| Single evaluator, local execution | The POC is desktop-first with no session isolation; concurrent users sharing a backend are not supported |
| Azure OpenAI is reachable with both deployments provisioned | `gpt-5.1-chat` (chat) and `text-embedding-3-large` (embedding) must exist under the configured endpoint |
| Session is transient | Conversation history lives in React state; a browser refresh starts a new session — no persistence layer is included by design |
| ChromaDB embedded in a named Docker volume is sufficient | There is no shared vector store across replicas; horizontal scaling is out of scope |

> Full decision rationale and architectural alternatives considered: [`docs/tasks/editorial-ai-poc.plan.md`](docs/tasks/editorial-ai-poc.plan.md)

---

## Trade-offs and what's deferred

| Area | Current state | Deferred work |
|---|---|---|
| **RAG depth** | Basic semantic retrieval — `analyze_query` decomposes to sub-queries, top-k chunks retrieved and ranked globally. No reranking, no HyDE, no hybrid BM25+vector, no contextual chunk enrichment. | Phase 8 spike: reranker, HyDE, hybrid BM25+vector search, contextual retrieval (prepend a short LLM-generated sentence to each chunk before embedding so it carries document-level context when retrieved in isolation), RAGAS evaluation harness. |
| **Auth** | None — the API is open; the app is single-user by design for the POC. | Add OAuth or API-key middleware before any shared deployment. |
| **Persistent history** | Session is fully transient — no `localStorage`, no database. Refreshing the page starts a new conversation. | Persist to SQLite or a backend session store for multi-turn production use. |
| **Production book storage** | HTML files are `COPY`'d into the Docker image at build time. Adding a book requires a rebuild. | Move to a managed blob store (S3, Azure Blob) with a dynamic ingest endpoint. |

# Architecture & Code Orientation

> Code is the source of truth. This doc orients agents to where things live and how the pieces connect — not what the code says.

---

## System overview

Two Docker services plus a one-shot ingestion tool, backed by Azure OpenAI and a local ChromaDB vector store.

```
┌─────────────────────────────────────────────────────┐
│  Docker Compose                                      │
│                                                      │
│  frontend  :3000          backend  :8000             │
│  React + Vite  ──HTTP/SSE──▶  FastAPI                │
│                                    │                 │
│                             ChromaDB (named volume)  │
│                             /app/data/chroma         │
└─────────────────────────────────────────────────────┘
                                     │
                              Azure OpenAI
                      text-embedding-3-large  /  gpt-5.1-chat
```

`ingest.py` is a **one-shot CLI** — it runs once before starting the app, populates ChromaDB, and exits. It is not part of the running backend.

---

## Data flows

**Ingestion (run once):**
```
books shared/*.html
  → core/ingestion.py   parse + chunk (chapter-aware, ~500 token chunks)
  → core/citations.py   populate excerpt + compose headings
  → core/embeddings.py  batch embed via Azure OpenAI (batches of 100)
  → ChromaDB            single "books" collection, tagged by book_id
```

**Chat (every request):**
```
React  POST /api/chat {book_id, message, history}
  → core/query_analysis.py  analyze_query() → 1–2 sub-queries with book targets
  → core/embeddings.py      embed each sub-query
  → core/retrieval.py       retrieve() — one ChromaDB query per sub-query,
                            dedup by chunk ID (highest score), return top-5 context + top-3 citable
  → core/prompts.py         build_system_prompt() + build_messages()
  → GPT chat call with assembled messages
  → SSE stream: tokens → sources event → done event
  → React renders progressively; source cards appear on done
```

---

## Directory map

```
book-publishing-company/
├── backend/
│   ├── core/
│   │   ├── ingestion.py       parse_book(), chunk_book(), ingest_book()
│   │   ├── citations.py       build_excerpt(), compose_heading(), populate_excerpts()
│   │   ├── embeddings.py      embed_texts(texts, batch_size=100)
│   │   ├── query_analysis.py  analyze_query() — LLM-based sub-query decomposition
│   │   ├── retrieval.py       retrieve() — multi-sub-query ChromaDB retrieval + merge
│   │   └── prompts.py         build_system_prompt(), build_messages()
│   ├── api/
│   │   ├── deps.py            FastAPI lifespan — ChromaDB + AzureOpenAI singletons
│   │   └── routes/
│   │       ├── books.py       GET /api/books — list ingested books with chapter counts
│   │       └── chat.py        POST /api/chat — SSE streaming RAG pipeline
│   ├── ingest.py              one-shot ingestion CLI (not imported by the app)
│   ├── main.py                FastAPI app — CORS, lifespan, routers, health check
│   ├── tests/
│   │   ├── test_ingestion.py    7 offline assertions — parser + citation output
│   │   ├── test_citations.py    citation unit tests
│   │   ├── test_query_analysis.py  analyze_query decomposition + repair logic
│   │   ├── test_retrieval.py    multi-sub-query retrieval, dedup, score merge
│   │   ├── test_prompts.py      system prompt and message assembly
│   │   ├── test_books.py        books route aggregation logic
│   │   ├── test_chat.py         chat route — SSE contract, embedding pipeline, error handling
│   │   └── test_main.py         health endpoint — no app.state dependency
│   ├── requirements.txt     runtime deps (fastapi, openai, chromadb, …)
│   ├── requirements-dev.txt pytest — installed only when INSTALL_DEV=true
│   └── Dockerfile
├── frontend/
│   ├── eslint.config.js
│   └── src/
│       ├── App.jsx          stateful shell — owns messages[], currentBookContext, isLoading; calls streamChat
│       ├── main.jsx         entry point — imports globals.css
│       ├── components/
│       │   ├── AppHeader.jsx
│       │   ├── AssistantMessage.jsx  amber left-rule, dots when !content, text once tokens arrive
│       │   ├── BookToggle.jsx        3-segment pill with inline SVG book glyph
│       │   ├── ChatInput.jsx         auto-expanding textarea, two disabled states
│       │   ├── ChatPanel.jsx         layout shell: CONVERSATION divider + body slot + ChatInput
│       │   ├── MessageList.jsx       maps messages[] → UserMessage/AssistantMessage/SourceList; auto-scroll sentinel
│       │   ├── SourceCard.jsx        chapter-line formatting, 4-line excerpt clamp
│       │   ├── SourceList.jsx        flex: 1 1 0 equal-width card row
│       │   ├── UserMessage.jsx
│       │   └── WelcomeState.jsx
│       ├── lib/
│       │   ├── messageHelpers.js     pure reducers: applyToken, applySources, applyDone, applyError, buildTimestamp
│       │   ├── messageHelpers.test.js  7 vitest tests for message state transitions
│       │   ├── streamChat.js         SSE fetch client — partial-frame buffer pattern
│       │   └── streamChat.test.js    7 vitest tests covering AC 11 + AC 12
│       └── styles/
│           └── globals.css           design tokens, Google Fonts, all component CSS
├── books shared/            source HTML — COPY'd into /app/books/ at build time
│   ├── little_women.html
│   └── pride_prejudice.html
├── docker-compose.yml
└── docs/
    ├── architecture.md      ← this file
    ├── design/              Mowgli screenshots + spec (Phase 1)
    └── tasks/               story scaffolding (plan + per-story design/tasks/tracker)
```

---

## Key decisions worth knowing

| Decision | Where it matters |
|----------|-----------------|
| Single `"books"` ChromaDB collection; `book_id` field filters per-book | `ingest.py`, `api/routes/` (Phase 4) |
| `None` metadata values rejected by ChromaDB — omit keys when absent | `ingest.py` metadata loop |
| Multi-key `where` needs `$and` wrapper | any ChromaDB query with two conditions |
| `collection.upsert()` not `add()` — re-ingest safe | `ingest.py` |
| Chunk IDs: `{book_id}_ch{n:03d}_chunk{i:03d}` — deterministic | `ingest.py` |
| `response.data` sorted by `.index` before extending embeddings list | `core/embeddings.py` |
| Conversation history tagged with scope to prevent cross-book bleed | `core/prompts.py` (Phase 4) |
| SSE sources event sent after all tokens, not inline | `api/routes/` (Phase 4) |

Full rationale for every decision is in `docs/tasks/editorial-ai-poc.plan.md`.

---

## Running things

```bash
# First-time setup
cp .env.template .env   # fill in Azure OpenAI credentials

# Ingest books (run once; re-running is safe — upsert)
docker compose build backend
docker compose run --rm backend python ingest.py

# Start the app
docker compose up

# Run tests (offline — no Azure needed)
docker compose run --rm backend python -m pytest tests/ -v
```

Required `.env` keys: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.

---

## Phase status

| Phase | What | Status |
|-------|------|--------|
| 2 | Docker Compose scaffold, FastAPI skeleton, React + Vite skeleton | ✅ done |
| 3 | Book ingestion pipeline (parse → cite → embed → store) | ✅ done |
| 4 Story 1 | RAG logic tier: deps, query_analysis, retrieval, prompts | ✅ done |
| 4 Story 2 | HTTP layer: `/api/chat` SSE route, `/api/books`, health endpoint | ✅ done (PR open, T4–T6 manual) |
| 5 Story 1 | Design system + presentational components (globals.css, streamChat.js, 8 UI components) | ✅ done (PR open) |
| 5 Story 2 | App composition (App.jsx, ChatPanel, MessageList, stateful wiring) | ✅ done (PR open; T4/T5 streaming verify deferred to Phase 6 — needs Vite proxy) |
| 6 | Integration + Docker smoke tests | pending |

---

## See also

- [`docs/api.md`](api.md) — HTTP endpoint contracts, SSE wire protocol, source object fields, `book_id` valid values (Phase 5 frontend reference)

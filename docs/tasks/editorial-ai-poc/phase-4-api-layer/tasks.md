---
name: phase-4-api-layer
plan: editorial-ai-poc
phase: "phase-4"
type: tasks
---

# Phase 4 API Layer — Tasks

Dependency-ordered. Tasks T1–T3 are `[AGENT]`; T4–T6 are `[MANUAL]`.

## Tasks

- [x] **T1** `[AGENT]` Write `backend/api/routes/books.py` — `GET /api/books`
  - **Output:** `books.py` APIRouter with one route that queries the ChromaDB `books` collection, aggregates distinct books, and returns a JSON list of `{id, title, chapter_count}` dicts
  - **Complexity:** Lightweight
  - **Depends on:** Story 1 (deps.py for the collection, accessed via `request.app.state`)
  - **Done when:** `GET /api/books` returns HTTP 200 with a list containing one entry per ingested book; each entry has `id` (matching `book_id` metadata), `title` (matching `book_title` metadata), and `chapter_count` (distinct `chapter_number` values for that book)

- [x] **T2** `[AGENT]` Write `backend/api/routes/chat.py` — `POST /api/chat` SSE
  - **Output:** `chat.py` APIRouter with one streaming route implementing the full RAG pipeline: analyze query → embed sub-queries (batched) → retrieve per sub-query → build prompt → stream completion → emit sources → emit done
  - **Complexity:** Full
  - **Depends on:** T1, Story 1 (query_analysis.py, retrieval.py, prompts.py, deps.py; `embed_texts` from core/embeddings.py)
  - **Done when:**
    - Request body accepts `book_id: str`, `message: str`, `history: list[dict]`
    - Response is `StreamingResponse` with `media_type="text/event-stream"`
    - Calls `analyze_query(message, book_id, openai_client)` to get 1–2 sub-queries before embedding
    - Embeds all sub-query strings in one `embed_texts()` call, pairs embeddings back with `book_id` per sub-query
    - Passes the paired list to `retrieve()`, not a single embedding
    - Streams `data: {"token": "..."}\n\n` for each token
    - Streams `data: {"sources": [...]}\n\n` after the last token, where sources are the top-3 citable chunks' metadata dicts
    - Streams `data: {"done": true}\n\n` as the final frame
    - `openai.BadRequestError` with `code == "content_filter"` yields `data: {"error": "Content filtered by Azure policy"}\n\n` then `data: {"done": true}\n\n`, does not raise
    - `scope_label` is derived from `book_id`: `little_women` → `"Little Women"`, `pride_prejudice` → `"Pride & Prejudice"`, `both` → `"both books"`

- [x] **T3** `[AGENT]` Write `backend/main.py` — FastAPI app wiring
  - **Output:** `main.py` creating the FastAPI app, registering CORS middleware, mounting the `books` and `chat` routers under `/api`, wiring the `lifespan` from deps.py, and exposing `GET /api/health`
  - **Complexity:** Standard
  - **Depends on:** T1, T2, Story 1
  - **Done when:** `uvicorn main:app` starts without error; `GET /api/health` returns `{"status": "ok"}`; CORS allows origins `http://localhost:3000` and `http://frontend:3000`; both routers are mounted with prefix `/api`

- [x] **T4** `[MANUAL]` Verify health endpoint
  - **Output:** confirmed 200 response
  - **Complexity:** Lightweight
  - **Depends on:** T3
  - **Done when:** `curl http://localhost:8000/api/health` returns `{"status":"ok"}`

- [x] **T5** `[MANUAL]` Test chat streaming end-to-end
  - **Output:** confirmed SSE token stream with source citations
  - **Complexity:** Lightweight
  - **Depends on:** T4
  - **Done when:** `curl -N -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"book_id":"little_women","message":"Who is Jo?","history":[]}'` streams token events and ends with a sources event containing LW chapter metadata, followed by `{"done":true}`

- [x] **T6** `[MANUAL]` Test scope containment
  - **Output:** confirmed the model stays within the active scope when history contains cross-scope turns
  - **Complexity:** Standard
  - **Depends on:** T5
  - **Done when:** a P&P question sent with `book_id: "little_women"` and a P&P-heavy `history` produces a response that stays inside Little Women or explicitly declines rather than answering from history

---
name: phase-4-api-layer
plan: editorial-ai-poc
phase: "phase-4"
type: story
status: pending
---

# Phase 4 API Layer — Design

## Output

A running FastAPI server exposing `GET /api/health`, `GET /api/books`, and `POST /api/chat` with SSE streaming — the full HTTP surface for Phase 4.

## Context

Story 2 builds the HTTP layer on top of the logic tier delivered by Story 1. `chat.py` is the most complex module in the phase: it orchestrates embed → retrieve → prompt → stream → emit-sources in a single SSE generator. `books.py` is a lightweight sanity endpoint. `main.py` wires everything together.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) §4 (API endpoints, Streaming implementation, Azure OpenAI integration notes)

## Decisions inherited from the plan

| Decision | Source |
| --- | --- |
| `POST /api/chat` is the only chat endpoint — `POST /api/compare` was cut | plan §4 "`POST /api/compare` is cut" |
| SSE wire format: `data: {"token": "..."}`, then `data: {"sources": [...]}`, then `data: {"done": true}` | plan §4 Chat endpoint design |
| Sources sent as a final event — keeps streaming simple; render tokens, then cards | plan §4 Chat endpoint design |
| `openai.BadRequestError` with `code == "content_filter"` → emit `{"error": "..."}` event, do not raise | plan §4 Azure OpenAI integration notes |
| `choice.message.refusal` → handle as error/warning | plan §4 Azure OpenAI integration notes |
| `fetch` + `ReadableStream` on the frontend — the SSE must be `text/event-stream` with `\n\n` frame separators | plan §5 Streaming in React |
| CORS must allow the Vite dev origin (`http://localhost:3000`) | plan §6 Docker Compose structure |
| `GET /api/health` returns 200 — Docker health check depends on it | docker-compose.yml |
| `GET /api/books` is not consumed by the UI — it is a sanity check and OpenAPI demo surface | plan §4 API endpoints |
| Query embedding uses `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` env var, same as `embeddings.py` | plan §4 / embeddings.py |

## Story-local design

**`chat.py` — generator sequence**

```
async def generate():
    # 1. analyze_query(message, book_id, openai_client) → sub_queries (1 or 2)
    # 2. embed_texts([sq["query"] for sq in sub_queries]) → embeddings list
    # 3. pair embeddings back: [{"query_embedding": emb, "book_id": sq["book_id"]} ...]
    # 4. retrieve(sub_query_inputs, collection) → (context_chunks, citable)
    # 5. build_system_prompt(scope_label) + build_messages(...)
    # 6. openai_client.chat.completions.create(stream=True, ...)
    # 7. async for chunk in completion: yield token events
    # 8. yield sources event (from citable)
    # 9. yield done event
```

The `try/except openai.BadRequestError` wraps step 6 only. If raised with `code == "content_filter"`, yield an error event and return. Any other `BadRequestError` re-raises.

`embed_texts` is called once for all sub-queries in a single batch (steps 2–3) — one embedding API call regardless of sub-query count.

**`scope_label` derivation**

`book_id` → `scope_label` mapping (used in system prompt and history tagging):

| `book_id` | `scope_label` |
| --- | --- |
| `little_women` | `"Little Women"` |
| `pride_prejudice` | `"Pride & Prejudice"` |
| `both` | `"both books"` |

This mapping lives in `chat.py` — it is a routing concern, not a prompt concern.

**`books.py` — response shape**

Queries the `books` collection for all documents, extracts distinct `(book_id, book_title, chapter_number)` per chunk, aggregates to `{id, title, chapter_count}` per book. Returns a JSON list. No Pydantic model needed — plain dicts suffice for a sanity endpoint.

**`main.py` — CORS origins**

Allow `http://localhost:3000` (Vite dev) and `http://frontend:3000` (Docker network). `allow_credentials=False`, `allow_methods=["*"]`, `allow_headers=["*"]`.

## Main files to change

- `backend/api/routes/books.py` — new: `GET /api/books` sanity endpoint
- `backend/api/routes/chat.py` — new: `POST /api/chat` SSE streaming route
- `backend/main.py` — new: FastAPI app factory, CORS, lifespan, router registration

## Acceptance criteria

- [ ] `GET /api/health` returns HTTP 200 with `{"status": "ok"}` — no `app.state` dependency
- [ ] `GET /api/books` returns a JSON list with an entry for each ingested book, including `id`, `title`, and `chapter_count`
- [ ] `POST /api/chat` with `book_id: "little_women"` streams token events followed by a sources event with `chapter_title` containing a real LW chapter name (e.g. `"Playing Pilgrims"`)
- [ ] `POST /api/chat` with `book_id: "both"` returns sources from both books in the same response
- [ ] A `book_id: "little_women"` request with a P&P-heavy history produces an answer that stays within Little Women scope or explicitly declines
- [ ] Azure content filter error (`BadRequestError` with `code == "content_filter"`) yields `data: {"error": "..."}` then `data: {"done": true}` — no 500
- [ ] The response `Content-Type` header is `text/event-stream`
- [ ] CORS headers present on responses to `http://localhost:3000` origin

## Out of scope

- Frontend implementation (Phase 5)
- Vite proxy config (Phase 6)
- Docker rebuild / full-stack compose test (Phase 6)
- Authentication, session persistence (deferred per plan §8)

## Risks

- **Partial SSE frame at the React consumer** — the `\n\n` separator is what React's `buffer.split("\n\n")` / `pop()` depends on. FastAPI's `StreamingResponse` with an async generator that yields `f"data: ...\n\n"` produces correct frames. Risk: accidentally yielding without the double newline breaks all downstream parsing.
- **`embed_texts` takes a list** — the helper was written for batch ingestion. Wrapping the single query string in a list (`embed_texts([message])`) and taking index 0 is correct; passing the string directly produces character-level embeddings.
- **Content filter on retrieval** — the filter fires at the completion call, not at embedding. Retrieval can succeed but the subsequent completion call may still be blocked on a filter hit. The `try/except` covers this correctly.

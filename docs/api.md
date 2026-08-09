# Backend API Reference

> Code is the source of truth. This doc captures the HTTP contract and SSE wire
> protocol so frontend agents don't have to reverse-engineer it from the backend.

---

## Endpoints

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| `GET` | `/api/health` | `main.py` | Docker health check — no credentials needed |
| `GET` | `/api/books` | `api/routes/books.py` | List ingested books (sanity + OpenAPI demo) |
| `POST` | `/api/chat` | `api/routes/chat.py` | SSE streaming RAG chat |

CORS allows `http://localhost:3000` and `http://frontend:3000`. `allow_credentials=False`.

---

## GET /api/health

No request body.

```json
{"status": "ok"}
```

---

## GET /api/books

No request body. Returns a JSON array — one entry per ingested book.

```json
[
  {"id": "little_women",    "title": "Little Women",       "chapter_count": 47},
  {"id": "pride_prejudice", "title": "Pride & Prejudice",  "chapter_count": 61}
]
```

---

## POST /api/chat

### Request

```json
{
  "book_id": "little_women",
  "message": "Who is Jo March?",
  "history": [
    {"role": "user",      "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

| Field | Type | Valid values | Notes |
|-------|------|-------------|-------|
| `book_id` | string | `little_women` · `pride_prejudice` · `both` | Validated at the API boundary — unknown values return 422 |
| `message` | string | any | The current user turn; do not include it in `history` |
| `history` | array | alternating user/assistant dicts | Prior turns only; empty array for a fresh conversation |

### Response

`Content-Type: text/event-stream`. Frames arrive in strict order:

```
data: {"token": "Jo"}
data: {"token": " March"}
...one frame per token...
data: {"sources": [...]}
data: {"done": true}
```

On error (content filter, model refusal, pipeline failure):

```
data: {"error": "Content filtered by Azure policy"}
data: {"done": true}
```

`{"done": true}` is **always** the final frame — the frontend can rely on this to know the stream is complete.

### SSE frame types

| Frame | When | Fields |
|-------|------|--------|
| `{"token": "..."}` | During generation | `token`: one or more characters |
| `{"sources": [...]}` | After last token | `sources`: array of source objects (see below) |
| `{"done": true}` | Always last | — |
| `{"error": "..."}` | On failure | `error`: human-readable message; followed immediately by `done` |

Each frame is separated by `\n\n`. Parse with `buffer.split("\n\n")` + strip `data: ` prefix + `JSON.parse`. Do not use `EventSource` — the endpoint is a POST.

### Source object

Returned inside the `sources` array. Fields come from ChromaDB chunk metadata (set during ingestion).

| Field | Type | Example |
|-------|------|---------|
| `book_id` | string | `"little_women"` |
| `book_title` | string | `"Little Women"` |
| `chapter_number` | integer | `14` |
| `chapter_title` | string | `"Secrets"` |
| `excerpt` | string | `"Jo was very busy in the garret…"` |
| `chunk_index` | integer | `0` (position within chapter) |
| `contains_letter` | boolean | `true` when the chunk includes an epistolary letter |

Up to 3 sources per response. Frontend renders these as source cards below the completed assistant message.

---

## book_id → scope label mapping

The backend derives a human-readable `scope_label` from `book_id` and uses it in the system prompt and conversation history tagging. The frontend should use the same labels in its UI.

| `book_id` | Display label |
|-----------|--------------|
| `little_women` | Little Women |
| `pride_prejudice` | Pride & Prejudice |
| `both` | Both Books |

---

## Backend app state (for backend agents)

Singletons are initialised in `api/deps.py` via FastAPI's `lifespan` context and stored on `app.state`. Route handlers access them via `request.app.state`.

| Attribute | Type | Value |
|-----------|------|-------|
| `app.state.chroma_collection` | `chromadb.Collection` | The `"books"` collection from `./data/chroma` |
| `app.state.openai_client` | `openai.AzureOpenAI` | Sync client; used for chat completions in `chat.py` |
| `app.state.openai_deployment` | `str` | Value of `AZURE_OPENAI_DEPLOYMENT` env var |
| `app.state.openai_embedding_deployment` | `str` | Value of `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` env var |

`embed_texts()` in `core/embeddings.py` creates its own `AzureOpenAI` client from env vars internally — it does not use `app.state.openai_client`. Call it directly for embedding work.

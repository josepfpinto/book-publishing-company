---
name: phase-4-rag-core
plan: editorial-ai-poc
phase: "phase-4"
type: tasks
---

# Phase 4 RAG Core — Tasks

Dependency-ordered. All tasks are `[AGENT]`. No blocking unknowns remain.

## Tasks

- [x] **T1** `[AGENT]` Write `backend/api/deps.py` — client singletons
  - **Output:** `deps.py` with a `lifespan` async context manager that assigns `app.state.chroma_collection` (a `chromadb.Collection`) and `app.state.openai_client` (an `openai.AzureOpenAI` instance) on startup, and tears them down cleanly on shutdown
  - **Complexity:** Standard
  - **Depends on:** —
  - **Done when:** `deps.py` imports cleanly; `lifespan` signature matches FastAPI's expected `(app: FastAPI) -> AsyncGenerator`; env vars read are `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`; ChromaDB client points to `./data/chroma`

- [x] **T2** `[AGENT]` Write `backend/core/query_analysis.py` — always-on query decomposition
  - **Output:** `query_analysis.py` with `analyze_query(message: str, book_id: str, openai_client) -> list[dict]` — returns 1 or 2 dicts, each `{"query": str, "book_id": str}`. Uses a non-streaming LLM call with `response_format={"type": "json_object"}`. Falls back to `[{"query": message, "book_id": book_id}]` on any parse or API error.
  - **Complexity:** Standard
  - **Depends on:** T1 (openai_client)
  - **Done when:** passing `book_id="both"` always returns 2 items with distinct `book_id` values (`little_women` and `pride_prejudice`); passing a simple single-book question returns 1 item; passing a clearly compound single-book question (e.g. "What happens in chapter 1 and what happens at the end?") returns 2 items with the same `book_id`; a simulated JSON parse failure returns the fallback without raising

- [x] **T3** `[AGENT]` Write `backend/core/retrieval.py` — multi-sub-query retrieval with score merge
  - **Output:** `retrieval.py` with `retrieve(sub_queries: list[dict], collection, n_results: int = 5) -> tuple[list[dict], list[dict]]` — runs one ChromaDB query per sub-query (each with `where={"book_id": ...}` matching that sub-query's `book_id`), deduplicates results across sub-queries by chunk ID (keeping highest score), sorts by score descending, returns `(context_chunks[:5], context_chunks[:3])` as `(context_chunks, citable)`. Each dict contains the chunk's document text plus its raw ChromaDB metadata.
  - **Complexity:** Standard
  - **Depends on:** T1
  - **Done when:** each sub-query entry triggers exactly one ChromaDB `query()` call with its specific `book_id` filter; duplicate chunk IDs across sub-query results are collapsed to the highest-scoring copy; `citable` has at most 3 items; no `None` values in any returned metadata dict

- [x] **T4** `[AGENT]` Write `backend/core/prompts.py` — system prompt + message builder
  - **Output:** `prompts.py` with `build_system_prompt(scope_label: str) -> str` and `build_messages(system_prompt: str, history: list[dict], context_chunks: list[dict]) -> list[dict]`
  - **Complexity:** Standard
  - **Depends on:** —
  - **Done when:** `build_system_prompt` produces a string containing the `scope_label` and instructs the model to answer only from retrieved passages and cite book/chapter; `build_messages` returns a list starting with `{"role": "system", "content": system_prompt}` followed by history turns each with `[asked under: {scope_label}]` appended to their `content`, followed by the context passages formatted as `[CHUNK n] Book: {book_title} | {chapter_heading}\n"{text}"` — the user's current question is already the last item in `history` and is passed through unmodified; the function signature does NOT take the current question as a separate parameter

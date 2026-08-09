---
name: phase-4-rag-core
plan: editorial-ai-poc
phase: "phase-4"
type: story
status: pending
---

# Phase 4 RAG Core — Design

## Output

Four importable backend modules — `deps.py`, `query_analysis.py`, `retrieval.py`, `prompts.py` — that form the pure RAG and Azure client layer, with no HTTP surface.

## Context

Phase 4 builds the full AI assistant backend. This story establishes the logic tier first: client singletons, retrieval, and prompt construction. The API layer (Story 2) imports from all three. Writing logic without HTTP first means it can be read, reviewed, and reasoned about independently.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) §4 (Backend Strategy)

## Decisions inherited from the plan

| Decision | Source |
| --- | --- |
| ChromaDB `PersistentClient` at `./data/chroma`, single `books` collection | plan §4 ChromaDB setup |
| Query top-5 per sub-query, prompt on merged top-5, return merged top-3 as `sources` payload | plan §4 RAG retrieval (extended — see Story-local design) |
| Multi-condition `where` must use `$and` syntax — two bare keys are rejected by Chroma | plan §4 ChromaDB setup |
| AzureOpenAI client: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION` | plan §4 / embeddings.py convention |
| System prompt states the active scope and tags each prior turn with `[asked under: {scope}]` | plan §4 "Conversation history and book scope" |
| Active scope labels: `"Little Women"` \| `"Pride & Prejudice"` \| `"both books"` | plan §4 prompts.py |
| Chunk metadata is verbatim ChromaDB metadata — frontend composes the citation line from it | plan §4 Citation schema |

## Story-local design

**`deps.py` — singleton strategy**

FastAPI's `lifespan` context manager is the right hook for creating and tearing down long-lived clients. A module-level global (assigned inside `lifespan`) is the simplest shape here — no dependency-injection framework, just `app.state`. The chat route reads `request.app.state.chroma_collection` and `request.app.state.openai_client`.

**`query_analysis.py` — always-on query decomposition**

Every request — single-book or cross-book — passes through a lightweight LLM call that decides whether the user's question should become one or two sub-queries.

```
analyze_query(message: str, book_id: str, openai_client) -> list[dict]
# Returns 1 or 2 items: [{"query": str, "book_id": str}, ...]
```

Decision rules the LLM follows (baked into the analysis prompt):

| `book_id` | Rule |
| --- | --- |
| `"both"` | Always return 2 sub-queries, each tailored to one book and tagged with its `book_id` |
| single book | Return 1 sub-query (refined restatement of the question) unless the question clearly contains 2 separable parts, in which case return 2, both tagged with the same `book_id` |

The call is non-streaming and uses `response_format={"type": "json_object"}` so the output is always parseable. The prompt lives in `query_analysis.py` alongside the function — it is a self-contained analysis concern, not a chat prompt concern, so it does not belong in `prompts.py`.

**`retrieval.py` — multi-sub-query retrieval with merge**

The function now takes a list of sub-queries (already embedded by the route) and returns the merged top results:

```
retrieve(
    sub_queries: list[dict],   # each: {"query_embedding": list[float], "book_id": str}
    collection,
    n_results: int = 5
) -> tuple[list[dict], list[dict]]   # (context_chunks, citable)
```

For each sub-query, it runs a ChromaDB `query()` with the sub-query's embedding and a `where={"book_id": ...}` filter (no filter only when `book_id == "both"` with no sub-query book target — but since `analyze_query` always tags sub-queries with a specific book for the "both" case, the filter is always present). Results across sub-queries are deduplicated by chunk ID (keeping the highest score for any duplicate), then sorted by score descending. `context_chunks` = top 5; `citable` = top 3.

Why query tailoring (not score manipulation) is what provides balance: a sub-query rewritten to focus on Elizabeth Bennet will score P&P chunks highly; one rewritten for Jo March will score LW chunks highly. Both books' top chunks enter the candidate pool naturally — the merge then selects the globally best results from a balanced set.

**`prompts.py` — two entry points (unchanged shape)**

1. `build_system_prompt(scope_label: str) -> str` — returns the system prompt string with scope substituted.
2. `build_messages(system_prompt: str, history: list[dict], context_chunks: list[dict]) -> list[dict]` — assembles the full OpenAI messages array: system message, history turns with scope tags, then the user's current question. History is already included in the caller's `history` list; the current message is the last item.

The scope tag format: `[asked under: {scope_label}]` appended to each history message's content before sending to the model.

## Main files to change

- `backend/api/deps.py` — new: ChromaDB collection singleton + AzureOpenAI client singleton, both wired via FastAPI lifespan
- `backend/core/query_analysis.py` — new: `analyze_query(message, book_id, openai_client)` → list of 1–2 sub-queries with book targets
- `backend/core/retrieval.py` — new: `retrieve(sub_queries, collection)` → `(context_chunks, citable)`; runs one ChromaDB query per sub-query, deduplicates, merges by score
- `backend/core/prompts.py` — new: `build_system_prompt(scope_label)` + `build_messages(system_prompt, history, context_chunks)`

## Acceptance criteria

- [ ] `deps.py` exports a `lifespan` async context manager that assigns `app.state.chroma_collection` and `app.state.openai_client` on startup
- [ ] `query_analysis.py` returns exactly 2 sub-queries when `book_id == "both"`, each tagged with a different `book_id` (`little_women` and `pride_prejudice`)
- [ ] `query_analysis.py` returns 1 sub-query for a simple single-book question and 2 for a clearly compound single-book question
- [ ] `retrieval.py` runs one ChromaDB query per sub-query entry, each with `where={"book_id": ...}` matching that entry's `book_id`
- [ ] `retrieval.py` deduplicates results across sub-queries by chunk ID and returns `citable` with at most 3 items sorted by score descending
- [ ] `prompts.py` `build_system_prompt` includes the scope label and instructs the model to answer only from retrieved passages
- [ ] `prompts.py` `build_messages` appends `[asked under: {scope_label}]` to every history turn's `content`
- [ ] No metadata value of `None` passes through `retrieval.py`

## Out of scope

- HTTP routes and app wiring (Story 2)
- SSE streaming (Story 2)
- Embedding sub-queries — `retrieval.py` accepts pre-computed embeddings; embedding happens in the route (Story 2) using `embed_texts`
- Post-hoc score manipulation to force book balance — query tailoring provides balance naturally

> **Plan conflict (not silently resolved):** The plan §4 states "There is no separate compare path and no per-book merge step." This story implements a per-sub-query retrieval with merge, which contradicts that decision. The plan's §4 RAG retrieval section should be updated via `/shape` or during `/archive-and-cleanup` to reflect the always-on query decomposition approach chosen here.

## Risks

- **`analyze_query` adds latency** — one non-streaming LLM call before retrieval, ~100–200ms. Acceptable for a POC demo; the streaming response still starts immediately after this step.
- **JSON parse failure from LLM** — if `response_format={"type": "json_object"}` returns malformed JSON or an unexpected schema, `query_analysis.py` must fall back to a single sub-query using the original message and the original `book_id`. Never crash the request on an analysis failure.
- **ChromaDB `$and` syntax** — a `where` with two bare keys raises on both 0.6 and 1.5. For this story the only filter key per sub-query is `book_id`, so a plain `{"book_id": ...}` dict is correct and `$and` is not needed.
- **`app.state` availability in routes** — the lifespan approach means the collection and client are `None` before `lifespan` runs. The health endpoint (Story 2) must not read `app.state` — it should return 200 with no dependency.

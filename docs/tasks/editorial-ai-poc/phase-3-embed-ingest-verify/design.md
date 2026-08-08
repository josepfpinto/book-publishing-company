---
name: phase-3-embed-ingest-verify
plan: editorial-ai-poc
phase: "phase-3"
type: story
status: pending
---

# Embed + Ingest + Verify — Design

## Output

`backend/core/embeddings.py`, `backend/ingest.py`, and `backend/tests/test_ingestion.py`: a batch embedding helper, the one-shot ingestion CLI, and the six-assertion verification gate — resulting in a populated ChromaDB `books` collection that passes all ingestion tests.

## Context

Phase 3, Story 2. This story consumes the parsing and citation modules from Story 1 and wires them to Azure OpenAI embeddings and ChromaDB storage. The ingestion CLI (`ingest.py`) is a one-shot tool run inside Docker; it is not part of the FastAPI application. Phase 4 (AI Assistant Backend) reads from the `books` collection this story creates.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) §4 — ChromaDB setup, chunk metadata schema, ChromaDB metadata constraints, batch embedding, ingestion verification gate.

## Decisions inherited from the plan

| Decision | Source |
| -------- | ------ |
| Single `books` collection — single-book = `where={"book_id": ...}`; cross-book = no filter | plan §4 ChromaDB setup |
| Persistent ChromaDB client writing to `./data/chroma` | plan §4 |
| `chromadb==1.5.*` (not 0.6.*) — 0.6.3 prints telemetry errors to stderr on every operation | plan §4 |
| `None` metadata values rejected by ChromaDB — omit optional keys when absent | plan §4 ChromaDB metadata constraints |
| Multi-key `where` needs `$and` wrapper — bare two-key dict raises on both versions | plan §4 |
| `text-embedding-3-large` via `openai==1.57.*` AzureOpenAI sync client | plan §4 key Python dependencies |
| Embed in batches of 100 | plan §4 Book ingestion parsing strategy |
| Ingestion is one-shot CLI: `docker compose run --rm backend python ingest.py` | plan §6 Ingestion flow |
| Books at `/app/books/` inside the Docker container (from Dockerfile `COPY ["books shared/", "/app/books/"]`) | plan §6 Docker Compose + Dockerfile |
| Six ingestion gate assertions — all test parser/chunker output, all runnable offline | plan §4 Ingestion verification gate |

## Story-local design

- Book paths in `ingest.py` use `os.getenv("BOOKS_DIR", "books")` — resolves to `/app/books` inside Docker (via WORKDIR `/app`), overridable in local dev.
- Chunk IDs: `f"{book_id}_ch{chapter_number:03d}_chunk{chunk_index:03d}"` — deterministic and re-runnable with `get_or_create_collection()`.
- `text` key is the ChromaDB `document` argument, not a metadata field.
- Tests use `scope="module"` fixtures to parse both books once, keeping the full test run fast (< 5s offline).
- After the MANUAL `ingest.py` run, delete `docs/tasks/editorial-ai-poc.parser-probe.py` — the plan says to remove it once production `ingestion.py` + `citations.py` exist.

## Main files to change

- `backend/core/embeddings.py` — new file; batch embedding helper
- `backend/ingest.py` — new file; ingestion CLI
- `backend/tests/__init__.py` — new file (empty, makes `tests/` a package for pytest)
- `backend/tests/test_ingestion.py` — new file; six-assertion gate

## Acceptance criteria

- [ ] `python ingest.py` runs to completion inside Docker with exit code 0
- [ ] Both books ingested: stdout reports 47 LW chapters and 61 P&P chapters with chunk counts
- [ ] All six pytest gate assertions pass: `pytest tests/test_ingestion.py -v` → 6 passed
- [ ] ChromaDB `books` collection contains chunks with correct metadata (verifiable via `collection.count()`)
- [ ] No `None` or `""` values in stored metadata
- [ ] `embed_texts()` batches in groups of ≤ 100 (no single-text-per-call loop)
- [ ] `parser-probe.py` deleted after gate passes

## Out of scope

- FastAPI endpoints (Phase 4)
- Frontend (Phase 5)
- RAG retrieval (Phase 4)
- Re-ingestion / update flows (fixed 2-book dataset)

## Risks

- Azure OpenAI rate-limit during ingestion: ~840 chunks ÷ 100 per batch = ~9 API calls. At eval account rates this is negligible, but a transient 429 will abort the run. No retry logic for POC — re-run if it fails.
- ChromaDB embedding dimension mismatch if re-ingesting after switching embedding models: delete the volume first (`docker volume rm book-publishing-company_chroma_data`).
- Tests run the real HTML parser on both books (no mocks) — they take ~1–2s each on first run. Module-scope fixtures keep the total test suite fast.

---
name: phase-3-embed-ingest-verify
plan: editorial-ai-poc
phase: "phase-3"
type: tasks
---

# Embed + Ingest + Verify — Tasks

Dependency-ordered. Every task is tagged `[MANUAL]` or `[AGENT]` and states its output.

## Tasks

- [x] **T1** `[AGENT]` Write `backend/core/embeddings.py`
  - **Output:** `backend/core/embeddings.py` — exports `embed_texts(texts, batch_size=100) -> list[list[float]]`; batches API calls; reads credentials from env
  - **Complexity:** Standard
  - **Depends on:** —
  - **Done when:** function signature matches spec; batching implemented (not one call per text); all four env vars read

  ---

  ## Goal
  Produce `backend/core/embeddings.py` — a thin batch embedding helper used by `ingest.py` to vectorise ~840 chunks via Azure OpenAI in groups of 100.

  ## Context
  The plan §4 specifies `text-embedding-3-large` via `openai==1.57.*` AzureOpenAI sync client. Credentials come from environment variables loaded via `python-dotenv`. This is a CLI context (not async). The function is called once during ingestion.

  ## Executor
  AI agent.

  ## Reviewer expertise
  Expert. No scaffolding needed.

  ## Execution prompt

  ### Context
  You are implementing `backend/core/embeddings.py` for an editorial AI POC. The module wraps Azure OpenAI's embeddings endpoint to batch-embed up to ~840 text chunks. Plan §4 specifies `openai==1.57.*` AzureOpenAI sync client. Credentials in environment: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.

  ### What to produce
  A Python module at `backend/core/embeddings.py` exporting:

  ```python
  def embed_texts(texts: list[str], batch_size: int = 100) -> list[list[float]]:
      """Embed a list of texts via Azure OpenAI in batches.
      Returns a flat list of embedding vectors in the same order as input."""
  ```

  Use `openai.AzureOpenAI` (sync client). Call `load_dotenv()` at module level. Loop over `range(0, len(texts), batch_size)`, call `client.embeddings.create(input=batch, model=deployment)`, extract from `response.data[i].embedding`. Print batch progress to stderr.

  ### How to approach this
  1. Instantiate `AzureOpenAI` client with env vars at module level (or in the function — either is fine).
  2. Loop in batches; preserve order by extending a result list.
  3. Print: `f"Embedding batch {i//batch_size + 1}/{math.ceil(len(texts)/batch_size)}..."` to stderr.
  4. Keep the module under 40 lines — this is intentionally thin.

  ### Tone and behaviour
  Minimal. No retry logic, no fallback models, no telemetry. This is a POC helper.

  ## Validation

  ### Human review checklist
  - [ ] Single exported function with the exact signature above
  - [ ] Batches by `batch_size` — loop evident in the code (not `texts` passed whole)
  - [ ] All four env vars read (endpoint, key, API version, deployment)
  - [ ] Return list length guaranteed equal to input length

  ### If validation fails
  - *One call per text:* return the loop section with instruction to batch.
  - *Missing env var:* surgical fix to add `os.getenv(...)`.

---

- [x] **T2** `[AGENT]` Write `backend/ingest.py`
  - **Output:** `backend/ingest.py` — CLI that ingests both books into ChromaDB `books` collection; prints progress; exits 0 on success
  - **Complexity:** Standard
  - **Depends on:** T1 (embeddings.py); Story 1 T1 (ingestion.py); Story 1 T2 (citations.py)
  - **Done when:** script imports cleanly from `core.ingestion`, `core.citations`, `core.embeddings`; chunk IDs follow deterministic format; no `None` or `""` values in metadata dicts; uses `get_or_create_collection()`

  ---

  ## Goal
  Produce `backend/ingest.py` — the one-shot CLI that orchestrates parsing, citation population, batch embedding, and ChromaDB writes for both books.

  ## Context
  Run inside Docker: `docker compose run --rm backend python ingest.py`. Books at `/app/books/` (WORKDIR `/app`). ChromaDB persistent client at `./data/chroma`. Plan §4 specifies all metadata constraints. Plan §6 documents the ingestion flow.

  ## Executor
  AI agent.

  ## Reviewer expertise
  Expert. No scaffolding needed.

  ## Execution prompt

  ### Context
  You are implementing `backend/ingest.py` for an editorial AI POC. Read `book-publishing-company/docs/tasks/editorial-ai-poc.plan.md` §4 (ChromaDB setup, chunk metadata schema, metadata constraints) and §6 (ingestion flow) before writing any code.

  Book definitions:
  ```python
  import os
  BOOKS_DIR = os.getenv("BOOKS_DIR", "books")
  BOOKS = [
      {"path": f"{BOOKS_DIR}/little_women.html",    "book_id": "little_women",    "book_title": "Little Women"},
      {"path": f"{BOOKS_DIR}/pride_prejudice.html", "book_id": "pride_prejudice", "book_title": "Pride and Prejudice"},
  ]
  ```

  ### What to produce
  A Python script at `backend/ingest.py`. When run with `python ingest.py`:
  1. `load_dotenv()` — load `.env`
  2. Create/get ChromaDB collection: `chromadb.PersistentClient(path="./data/chroma").get_or_create_collection("books")`
  3. For each book: call `ingest_book()` → `populate_excerpts()` → separate texts from metadata → call `embed_texts()` → call `collection.add()`
  4. Print progress per book: `f"{book_title}: {len(chunks)} chunks ingested"` to stdout

  Chunk ID format: `f"{book_id}_ch{chapter_number:03d}_chunk{chunk_index:03d}"`

  `collection.add()` call structure:
  ```python
  collection.add(
      ids=ids,
      documents=texts,          # the "text" key from each chunk dict
      embeddings=embeddings,
      metadatas=metadatas,      # everything EXCEPT "text" key; no None values
  )
  ```

  Metadata preparation: for each chunk dict, pop `text` as the document; then build the metadata dict. `chapter_title` is always present (real title or `"Chapter {n}"` fallback) — do not omit it. The only remaining optional keys are `page_start` and `page_end` (P&P only) — omit when absent. If `excerpt` is still `""` after `populate_excerpts()`, log a warning and omit it.

  ### How to approach this
  1. Re-read plan §4 ChromaDB metadata constraints — no `None`, no `""`, multi-key `where` needs `$and`.
  2. Build metadata dicts with explicit conditional omission of optional keys.
  3. Separate `text` from metadata before calling `collection.add()`.
  4. Use `get_or_create_collection()` — makes re-ingest safe.

  ### Tone and behaviour
  Methodical. Log progress so the operator can see the pipeline is running. Faithful to the plan's exact spec.

  ## Validation

  ### Human review checklist
  - [ ] Book paths use `BOOKS_DIR` env var with `"books"` default — no hardcoded absolute paths
  - [ ] `collection.add()` has separate `documents`, `embeddings`, `metadatas`, `ids` arguments
  - [ ] No `None` or `""` values in any metadata dict (conditional omission visible in code)
  - [ ] Collection name is `"books"` (≥ 3 chars)
  - [ ] Uses `get_or_create_collection()` not `create_collection()`

  ### If validation fails
  - *Hardcoded absolute path:* surgical fix to `os.getenv("BOOKS_DIR", "books")`.
  - *`None` in metadata:* return the metadata-building section with the conditional omission pattern.

---

- [x] **T3** `[AGENT]` Write `backend/tests/test_ingestion.py`
  - **Output:** `backend/tests/test_ingestion.py` and `backend/tests/__init__.py` — six pytest tests implementing the ingestion verification gate; all run offline without Azure OpenAI
  - **Complexity:** Standard
  - **Depends on:** Story 1 T1 (ingestion.py); Story 1 T2 (citations.py)
  - **Done when:** all six test functions present with the exact names below; `pytest --collect-only` shows 6 tests; fixture uses `scope="module"`
  - **Post-story note:** the gate is now **7** tests — `test_chapter_title_convention` was added later to cover plan §4 gate row 7 (the LW-real-title / P&P-fallback contract that `compose_heading()` keys off), which no test asserted. Unit coverage for the citation layer lives separately in `tests/test_citations.py`.

  ---

  ## Goal
  Produce `backend/tests/test_ingestion.py` — a pytest suite implementing the six ingestion gate assertions from plan §4, runnable offline without Azure OpenAI or ChromaDB.

  ## Context
  All six assertions test parser/chunker output — not embeddings or ChromaDB writes. They run the real HTML parser against the real book files (no mocks). Plan §4 maps each assertion to a defect that was actually observed in these files. Tests run inside Docker; books at `books/` relative to WORKDIR.

  ## Executor
  AI agent.

  ## Reviewer expertise
  Expert. No scaffolding needed.

  ## Execution prompt

  ### Context
  You are writing `backend/tests/test_ingestion.py` for an editorial AI POC. Read `book-publishing-company/docs/tasks/editorial-ai-poc.plan.md` §4 "Ingestion verification gate" before writing. All six assertions test parser + citation output — no embedding, no ChromaDB. Books at `books/` relative to WORKDIR (`/app` inside Docker); override with `BOOKS_DIR` env var.

  ### What to produce
  Two files:
  - `backend/tests/__init__.py` — empty
  - `backend/tests/test_ingestion.py` — pytest test file

  Use a `@pytest.fixture(scope="module")` named `all_chunks` that calls `ingest_book()` + `populate_excerpts()` for both books and returns the combined list. Implement exactly these six tests (names must match exactly):

  ```python
  def test_chapter_count_lw(all_chunks):
      # chunks for little_women contain chapter_numbers 1..47, all present, sequential

  def test_chapter_count_pp(all_chunks):
      # chunks for pride_prejudice contain chapter_numbers 1..61, all present, sequential

  def test_no_page_number_leakage(all_chunks):
      # no chunk's "text" matches re.search(r'\{[\divxlcIVXLC]+\}', text)

  def test_no_back_matter_leakage(all_chunks):
      # no chunk's "text" contains any of:
      # "The Works of Louisa May Alcott", "Transcriber's Note",
      # "Project Gutenberg", "START OF THE PROJECT"

  def test_chapter_first_chunk_open(all_chunks):
      # for each chapter's first chunk (chunk_index == 0), text[:1] is uppercase or in '"\'

  def test_metadata_schema(all_chunks):
      # every chunk has: book_title (str), chapter_number (int), excerpt (str)
      # excerpt ends on sentence punctuation (matches r'[.!?"…]$')
      # no value in the chunk dict is None
  ```

  Assertion messages must name the failing chunk: `f"{c['book_id']} ch{c['chapter_number']} chunk{c['chunk_index']}"`.

  ### How to approach this
  1. Write the `all_chunks` fixture first with `scope="module"` — runs once for the entire test session.
  2. For `test_chapter_count_lw` and `test_chapter_count_pp`: extract unique chapter numbers per book, assert they equal `set(range(1, N+1))`.
  3. For `test_chapter_first_chunk_open`: filter `chunk_index == 0` per chapter per book, check `text[:1]`.
  4. For `test_metadata_schema`: loop all chunks, check each required key exists, check type, check no `None`, check excerpt terminal character.

  ### Tone and behaviour
  Precise. Test names and assertion messages are documentation — make them exact and informative.

  ## Validation

  ### Human review checklist
  - [ ] All six test function names present and match the list exactly
  - [ ] Fixture uses `scope="module"` (not default function scope)
  - [ ] No mock or stub for `ingest_book` or `populate_excerpts`
  - [ ] Assertion messages include chunk identity (book_id + chapter + chunk_index)
  - [ ] `backend/tests/__init__.py` created (empty)

  ### If validation fails
  - *Missing test function:* add it surgically, do not regenerate the file.
  - *Function scope fixture (re-parses per test):* refactor fixture to `scope="module"`.

---

- [x] **T4** `[MANUAL]` Run ingestion inside Docker
  - **Output:** Both books vectorised and stored in the ChromaDB `books` collection; `ingest.py` exits 0
  - **Complexity:** Lightweight
  - **Depends on:** T1, T2, T3
  - **Done when:** `ingest.py` exits 0; stdout reports both books with chunk counts; no Python exceptions in output

  ## Goal
  Execute the ingestion pipeline inside Docker and confirm it completes without errors.

  ## Steps

  1. Build the backend image: `docker compose build backend`
  2. Run ingestion: `docker compose run --rm backend python ingest.py`
  3. Confirm stdout shows both books with chunk counts (LW ~400+ chunks, P&P ~440+ chunks).
  4. Check for any `ValueError` or `TypeError` in output (ChromaDB metadata rejections).
  5. If it fails with a rate-limit (HTTP 429), wait 60s and re-run.

  ## Done when
  - [x] `ingest.py` exits with code 0
  - [x] Stdout reports both books ingested with chunk counts

---

- [x] **T5** `[MANUAL]` Run gate tests + spot-check citations
  - **Output:** All six pytest assertions green; one LW and one P&P citation confirmed correctly formatted
  - **Complexity:** Lightweight
  - **Depends on:** T4
  - **Done when:** All 6 tests pass; both citation spot-checks confirm correct heading format; `parser-probe.py` deleted

  ## Goal
  Confirm the six ingestion gate assertions pass and both citation formats render correctly, then clean up the parser probe.

  ## Steps

  1. Run the gate: `docker compose run --rm backend python -m pytest tests/test_ingestion.py -v`
  2. Confirm all 6 tests pass (green). If any fail, surface the failure message to the `/execute` agent for a surgical fix.
  3. Spot-check a LW citation: run a quick ChromaDB query or read a chunk's metadata from the collection — confirm heading format is `Chapter N — Title` and excerpt ends on punctuation.
  4. Spot-check a P&P citation: confirm heading format is `Chapter N · p. X` or `Chapter N · pp. X–Y`.
  5. Delete `book-publishing-company/docs/tasks/editorial-ai-poc.parser-probe.py` (plan says: "Delete it once `core/ingestion.py` and `core/citations.py` exist").

  ## Done when
  - [x] All 6 pytest tests pass
  - [x] LW citation heading is `Chapter N — Title` format
  - [x] P&P citation heading is `Chapter N · p. X` or `Chapter N · pp. X–Y` format
  - [x] `docs/tasks/editorial-ai-poc.parser-probe.py` deleted — completed after the story closed; the box was left unticked while the tracker was marked `done`

---
name: phase-3-parse-cite
plan: editorial-ai-poc
phase: "phase-3"
type: tasks
---

# Parse + Cite — Tasks

Dependency-ordered. Every task is tagged `[MANUAL]` or `[AGENT]` and states its output.

## Tasks

- [x] **T1** `[AGENT]` Write `backend/core/ingestion.py` — Note: per-paragraph page tracking (not chapter-wide); smoke test asserts on failure
  - **Output:** `backend/core/ingestion.py` — exports `parse_book()`, `chunk_book()`, `ingest_book()`; produces a list of chunk dicts matching the schema below; correct chapter counts asserted by `tests/test_ingestion.py`
  - **Complexity:** Standard
  - **Depends on:** —
  - **Done when:** `ingest_book()` returns chunks from 47 LW chapters and 61 P&P chapters; no `None` values in any chunk dict
  - **Post-story note:** the `__main__` smoke block described below was superseded by `tests/test_ingestion.py` (which asserts the exact chapter *set*, not just the count) and removed. The parser probe it references has also been deleted — plan §4 is now authoritative.

  ---

  ## Goal
  Produce `backend/core/ingestion.py` — a production-grade HTML parser and chapter-aware text chunker for both Project Gutenberg books, implementing all six DOM-defect fixes from the plan.

  ## Context
  The parsing strategy is fully validated in `book-publishing-company/docs/tasks/editorial-ai-poc.parser-probe.py` — that probe is the authoritative reference. This module translates it into production code and adds chunking. `citations.py` (T2) depends on the chunk dict schema it produces. Story 2's `ingest.py` calls `ingest_book()` directly.

  ## Executor
  AI agent.

  ## Reviewer expertise
  Expert (Python / BeautifulSoup). No scaffolding needed.

  ## Execution prompt

  ### Context
  You are implementing `backend/core/ingestion.py` for an editorial AI POC. Read `book-publishing-company/docs/tasks/editorial-ai-poc.parser-probe.py` in full before writing any code — it implements and proves the complete DOM manipulation strategy for both books. Your job is to translate it into production code and add chunking. Also read `book-publishing-company/docs/tasks/editorial-ai-poc.plan.md` §4 (defect table, chunk metadata schema, ChromaDB metadata constraints).

  ### What to produce
  A Python module at `backend/core/ingestion.py` exporting:
  - `parse_book(html_path: str, book_id: str, book_title: str) -> list[dict]` — parses HTML, returns paragraph-level dicts
  - `chunk_book(paragraphs: list[dict], chunk_chars: int = 2000, overlap_chars: int = 320) -> list[dict]` — packs paragraphs into chunks
  - `ingest_book(html_path: str, book_id: str, book_title: str) -> list[dict]` — calls both; sets `excerpt: ""`

  Each chunk dict MUST contain exactly these keys (omit optional keys when the value is absent — **never write `None`**):

  ```python
  {
      "text": str,            # full chunk text (documents field for ChromaDB)
      "book_id": str,         # "little_women" | "pride_prejudice"
      "book_title": str,      # "Little Women" | "Pride and Prejudice"
      "chapter_number": int,  # 1-indexed
      "chapter_title": str,   # ALWAYS: real title for LW (e.g. "Playing Pilgrims"); "Chapter {n}" fallback for P&P
      "chunk_index": int,     # 0-indexed within chapter
      "page_start": str,      # P&P only — first print page in chunk; OMIT for LW
      "page_end": str,        # P&P only — last print page if differs from page_start; OMIT otherwise
      "contains_letter": bool, # True if ANY paragraph in chunk is in <blockquote>/.blockquot
      "excerpt": str,         # placeholder — set to "" here; citations.py fills it
  }
  ```

  Chunking: accumulate paragraphs until `len(text) >= chunk_chars`, then start a new chunk. Overlap: re-include the last `overlap_chars` of text from the prior chunk using trailing complete paragraphs only. Never split a paragraph across chunks.

  ### How to approach this
  1. Read `parser-probe.py` in full. Translate `load()`, `chapters_lw()`, `chapters_pp()`, `collect()`, `clean_text()` directly into `parse_book()` — do not reinvent the DOM logic.
  2. Re-read plan §4 defect table. Verify each of the 6 rows has a corresponding fix in your implementation.
  3. Implement `chunk_book()` — accumulate paragraphs, track page numbers across paragraphs in the chunk, set `contains_letter` to `True` when any paragraph in the chunk was in a `<blockquote>` / `.blockquot`.
  4. Set `excerpt: ""` — `citations.py` overwrites it.
  5. Add a `if __name__ == "__main__"` block that calls `ingest_book()` for both books and prints: book name, chapter count, total chunks.

  ### Tone and behaviour
  Methodical. Follow the probe's DOM approach exactly — do not substitute alternatives. If the probe's logic does not translate cleanly to production code, flag it in a comment rather than silently patching it.

  ## Validation

  ### Human review checklist
  - [x] Each of the 6 defects in plan §4 has a corresponding fix (check the defect table row by row against the code)
  - [x] Chunk dict schema matches exactly — no `None` values, optional keys absent when not applicable, `text` key present
  - [x] Chapter counts are `47` for LW and `61` for P&P — now asserted by `tests/test_ingestion.py` (was the `__main__` smoke block, since removed)
  - [x] Chunking never splits mid-paragraph (read one chapter's chunk list and verify paragraph boundaries)

  ### If validation fails
  - *Missing defect fix:* return only the affected lines with the defect row from the plan — surgical fix only, do not re-run the full module.
  - *Schema violation (`None` value or missing required key):* flag the specific key and which chapter triggers it.
  - *Chapter count mismatch:* structural failure — re-examine anchor detection against the probe.

---

- [x] **T2** `[AGENT]` Write `backend/core/citations.py` — Note: _SENT regex matches probe exactly (U+201D + U+0022); all 4 heading forms verified
  - **Output:** `backend/core/citations.py` — exports `build_excerpt()`, `compose_heading()`, `populate_excerpts()`; correct heading forms for both book types asserted by `tests/test_citations.py`
  - **Post-story note:** the `__main__` assertions below were the only coverage `compose_heading()` ever had, and CI never ran them. Migrated to `tests/test_citations.py`; the block was removed. Migration also surfaced a defect in `build_excerpt()` — see the `target` guard note in plan §4 Excerpt rule.
  - **Complexity:** Standard
  - **Depends on:** T1 (imports chunk dict schema from `ingestion.py`)
  - **Done when:** `compose_heading()` produces all three canonical forms from plan §4; `build_excerpt()` always ends on sentence punctuation or `…`; `populate_excerpts()` overwrites `excerpt: ""` placeholders in chunk dicts

  ---

  ## Goal
  Produce `backend/core/citations.py` — the citation composition layer with `build_excerpt()` (≥ 1 complete sentence) and `compose_heading()` (graceful degradation per plan §4 Citation schema).

  ## Context
  The excerpt and heading rules are fully specified in `book-publishing-company/docs/tasks/editorial-ai-poc.plan.md` §4 (Citation schema, Excerpt rule). The probe's `excerpt()` and `cite()` functions are the validated recipe. This module is called by Story 2's `ingest.py` to overwrite each chunk's `excerpt: ""` placeholder before ChromaDB writes.

  ## Executor
  AI agent.

  ## Reviewer expertise
  Expert. No scaffolding needed.

  ## Execution prompt

  ### Context
  You are implementing `backend/core/citations.py` for an editorial AI POC. Read `book-publishing-company/docs/tasks/editorial-ai-poc.plan.md` §4 (Citation schema, Excerpt rule) and `book-publishing-company/docs/tasks/editorial-ai-poc.parser-probe.py` (the `excerpt()` and `cite()` functions at the bottom) before writing any code.

  ### What to produce
  A Python module at `backend/core/citations.py` exporting:

  ```python
  def build_excerpt(text: str, target: int = 230, minimum: int = 80) -> str:
      """Extract >= 1 complete sentence from text.
      Split on sentence boundaries: r'(?<=[.!?""])\s+'
      Accumulate until len(out) >= minimum, stop before target.
      Append '...' only if excerpt is shorter than the full text."""

  def compose_heading(chapter_number: int, chapter_title: str,
                      page_start: str | None, page_end: str | None) -> str:
      """Compose the SourceCard chapter line.
      chapter_title is always present — detect the fallback form to suppress the dash.
      Rules (from plan §4):
        Base:    'Chapter {n}'
        +title:  ' — {chapter_title}'   only when chapter_title != f"Chapter {chapter_number}"
        +page:   ' · p. {page_start}'   when page_start present and same as page_end (or page_end absent)
        +pages:  ' · pp. {page_start}–{page_end}'  when both present and differ
      """

  def populate_excerpts(chunks: list[dict]) -> list[dict]:
      """Overwrite the 'excerpt' key in each chunk dict in-place.
      Returns the same list (modified)."""
  ```

  Use `—` (em dash) for chapter title separator and `·` (middle dot) for page separator, matching the plan's canonical forms: `Chapter 9 — Meg Goes to Vanity Fair`, `Chapter 26 · pp. 182–183`.

  ### How to approach this
  1. Translate the probe's `excerpt()` directly into `build_excerpt()` — the sentence regex is `r'(?<=[.!?""])\s+'`.
  2. Translate the probe's `cite()` into `compose_heading()` — flatten the parameters (no `d` dict, just the individual fields).
  3. Do NOT add workarounds for the two cosmetic artifacts documented in plan §4 (double-quote opening, small-caps opening). Leave them as-is for the POC.
  4. Add a `if __name__ == "__main__"` block with assertions covering all four cases:
     - `compose_heading(9, "Meg Goes to Vanity Fair", None, None)` → `"Chapter 9 — Meg Goes to Vanity Fair"`
     - `compose_heading(26, "Chapter 26", "182", "183")` → `"Chapter 26 · pp. 182–183"` (fallback title suppressed)
     - `compose_heading(26, "Chapter 26", "182", None)` → `"Chapter 26 · p. 182"`
     - `compose_heading(26, "Chapter 26", None, None)` → `"Chapter 26"` (pure fallback)

  ### Tone and behaviour
  Precise. The rules are fully specified — implement them exactly. No embellishment. If the spec is ambiguous on any edge case, flag it in a comment rather than inventing a resolution.

  ## Validation

  ### Human review checklist
  - [x] `compose_heading()` produces all four canonical forms — now parametrized in `tests/test_citations.py`
  - [x] `build_excerpt()` ends on sentence punctuation (`.`, `!`, `?`, `"`) — never mid-word (test with a multi-sentence string)
  - [x] Neither function has book-specific branching — metadata-conditional logic only
  - [x] The two cosmetic artifacts (double-quote, small-caps) are NOT worked around

  ### If validation fails
  - *Wrong heading separator (wrong dash/dot character):* surgical fix to the separator string.
  - *Excerpt cut mid-word:* the sentence regex is wrong — return `build_excerpt()` alongside the probe's regex.
  - *Book-specific `if book_id == ...` branch:* architectural failure — heading should be pure metadata-conditional. Return the function with the constraint.

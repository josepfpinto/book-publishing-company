---
name: phase-3-parse-cite
plan: editorial-ai-poc
phase: "phase-3"
type: story
status: pending
---

# Parse + Cite — Design

## Output

`backend/core/ingestion.py` and `backend/core/citations.py`: a production HTML parser + chapter-aware chunker and the citation composition layer that populates every chunk's `excerpt` and heading metadata.

## Context

Phase 3 of the editorial AI POC builds the ingestion pipeline for two Project Gutenberg HTML books. This story covers the pure-Python parsing and citation layers — no external API or database calls. Both modules run offline and are fully testable without Azure OpenAI or ChromaDB access.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) §4 — Book ingestion, defect table, chunk metadata schema, citation schema.

## Decisions inherited from the plan

| Decision | Source |
| -------- | ------ |
| Anchor-based chapter detection (not heading text) — 61/61 P&P chapters parse correctly; regex on heading text drops 4 | plan §4 defect table row 5 |
| `decompose()` before `get_text()` for page numbers — `span.pagenum` sits mid-word in 10 of 496 cases | plan §4 defect table row 1 |
| Drop-cap recovery: `span.letra img[alt]` → replace with `img[alt]` text | plan §4 defect table row 2 |
| Caption exclusion: `span.caption`, `div.caption` decomposed | plan §4 defect table row 3 |
| Chapter boundary on **any** `<h2>` — prevents LW ch. 47 absorbing back-matter | plan §4 defect table row 4 |
| `p.nind` without `.letra` = paragraph continuation — rejoin to prior para | plan §4 defect table row 6 |
| Chunk size ~500 tokens (~2000 chars), ~80-token overlap (~320 chars), never split a paragraph | plan §4 |
| `chapter_title` always present — for LW: real title; for books without titles (P&P): `"Chapter {n}"` fallback. No conditional omission. | plan §4 (updated) |
| Optional metadata keys omitted (not `None`) when absent — ChromaDB rejects `None` on both 0.6.x and 1.5.x | plan §4 ChromaDB metadata constraints |
| `excerpt` field = ≥ 1 complete sentence, sentence-boundary split, never cut mid-word, `…` only if truncated | plan §4 Excerpt rule |
| `compose_heading()` always starts with `Chapter {n}`, appends title and/or page only when present | plan §4 Citation schema |

## Story-local design

- `ingestion.py` exports three functions: `parse_book()`, `chunk_book()`, `ingest_book()` (convenience wrapper). The parser-probe (`docs/tasks/editorial-ai-poc.parser-probe.py`) is the authoritative reference for all DOM manipulation — translate it directly, do not reinvent.
- `citations.py` exports: `build_excerpt()`, `compose_heading()`, `populate_excerpts()`. The probe's `excerpt()` and `cite()` functions are the validated recipe.
- `ingest_book()` sets `excerpt: ""` as a placeholder; `populate_excerpts()` in `citations.py` fills it. This keeps the DOM extraction and citation logic in separate, independently testable units.
- Both modules include a `if __name__ == "__main__"` smoke-test block for inline validation during `/execute`.

## Main files to change

- `backend/core/ingestion.py` — new file; HTML parser + chunker
- `backend/core/citations.py` — new file; excerpt builder + heading composer

## Acceptance criteria

- [ ] `ingest_book("books/little_women.html", ...)` returns chunks from exactly 47 sequential chapters
- [ ] `ingest_book("books/pride_prejudice.html", ...)` returns chunks from exactly 61 sequential chapters
- [ ] No chunk text contains a page-number artifact matching `\{[\divxlcIVXLC]+\}`
- [ ] No chunk text contains back-matter strings (`"The Works of Louisa May Alcott"`, `"Transcriber's Note"`, `"Project Gutenberg"`)
- [ ] Every chapter's first chunk starts with an uppercase letter or quote mark
- [ ] All required chunk dict keys (`book_id`, `book_title`, `chapter_number`, `chapter_title`, `chunk_index`, `contains_letter`, `excerpt`) are present; no value is `None`
- [ ] `chapter_title` is the real title for LW chapters and `"Chapter {n}"` for P&P chapters
- [ ] `compose_heading()` produces `Chapter N` (when `chapter_title == "Chapter N"` and no page) / `Chapter N — Title` (LW real title) / `Chapter N · p. X` / `Chapter N · pp. X–Y` correctly for all four cases
- [ ] `build_excerpt()` always ends on sentence punctuation (`.`, `!`, `?`, `"`) or `…`, never mid-word

## Out of scope

- Embedding (Story 2)
- ChromaDB writes (Story 2)
- Tests (Story 2)
- `ingest.py` CLI (Story 2)
- Deleting `parser-probe.py` (Story 2 MANUAL cleanup step)

## Risks

- The probe uses `scope="module"` parsing — if both books are parsed in one Python process, BeautifulSoup may retain state. Use independent `load()` calls per book.
- The chunking overlap logic (re-include trailing paragraphs from the prior chunk) is the most novel piece relative to the probe — test the edge case where a single paragraph exceeds the chunk target size.

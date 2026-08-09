---
name: phase-6-packaging
plan: editorial-ai-poc
phase: "phase-6"
type: story
status: pending
---

# Packaging — Design

## Output

An updated `README.md` explaining the system's approach, decisions, and trade-offs, and a `.zip` archive of the project suitable for submission.

## Context

Phase 6.2 is a coordination story — it packages the outputs of the preceding stories. The README draft exists but covers only setup steps; the evaluator also needs the architecture rationale, key decisions, and trade-offs. The `.zip` is the deliverable handed to the interviewer.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) § Phase 6 §6.2, § Phase 7

## Decisions inherited from the plan

| Decision | Source |
| --- | --- |
| README must include: setup instructions, approach explanation, key decisions + trade-offs | plan §6.2 |
| `.zip` excludes: `.env`, `node_modules`, `__pycache__`, chroma data (`data/chroma`) | plan §6.2 |
| A draft README already exists at project root — update or replace, not add a second file | plan §6.2 |

## Story-local design

**README content structure** (update in place at `book-publishing-company/README.md`):

1. What it does (already present — keep)
2. Prerequisites + first-time setup (already present — keep)
3. Running the app (already present — keep)
4. **Architecture** — brief prose + the component table from plan §2; reference the mermaid diagram shape but render it in ASCII for plain-markdown compatibility
5. **Key decisions** — table format: Decision | Choice | Why (draw from plan §§2–6)
6. **Trade-offs and what's deferred** — condensed from plan §8

**`.zip` packaging:** run from the workspace so the archive root is `book-publishing-company/`. Standard excludes applied via `zip -r ... -x` patterns.

## Main files to change

- `book-publishing-company/README.md` — add Architecture, Key Decisions, Trade-offs sections
- `book-publishing-company-submission.zip` — created at workspace root (not committed to git; excluded by `.gitignore` if needed)

## Acceptance criteria

- [ ] `README.md` contains an Architecture section describing the component flow (ingest → query → stream)
- [ ] `README.md` contains a Key Decisions table with ≥5 rows covering: FastAPI/SSE, ChromaDB embedded, chapter-aware chunking, `fetch`+ReadableStream (not EventSource), conversation scope tagging
- [ ] `README.md` contains a Trade-offs / Deferred section referencing at least RAG depth spike and auth
- [ ] `.zip` can be extracted and `docker compose up --build` runs successfully from it
- [ ] `.zip` does not contain `.env`, `node_modules/`, `__pycache__/`, or `data/chroma/`

## Out of scope

- Phase 7 presentation deck — separate phase, not bundled here
- Publishing to any external host

## Risks

- **`node_modules` size:** if `npm install` has been run locally, the directory is large. The `-x` exclude must use a glob that catches nested `node_modules` (e.g. `-x "*/node_modules/*"`).
- **`.env` in zip:** the exclusion of `.env` is a security requirement. Verify it is absent from the archive after creation (`unzip -l` inspection).

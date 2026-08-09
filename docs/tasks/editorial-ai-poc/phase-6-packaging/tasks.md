---
name: phase-6-packaging
plan: editorial-ai-poc
phase: "phase-6"
type: tasks
---

# Packaging — Tasks

Dependency-ordered. Every task is tagged `[MANUAL]` or `[AGENT]` and states its output.

## Tasks

- [ ] **T1** `[AGENT]` Update `README.md` with architecture, key decisions, and trade-offs
  - **Output:** `book-publishing-company/README.md` updated in place with Architecture, Key Decisions, and Trade-offs/Deferred sections
  - **Complexity:** Standard
  - **Depends on:** —
  - **Done when:**
    - Existing setup/run sections are preserved
    - Architecture section describes the component flow: ingest → query → stream; includes component table (React, FastAPI, ChromaDB, `ingest.py`, Azure OpenAI)
    - Key Decisions table contains ≥5 rows covering: FastAPI + SSE, ChromaDB embedded mode, chapter-aware chunking, `fetch`+ReadableStream (not EventSource), conversation scope tagging in history
    - Trade-offs / Deferred section references at minimum: RAG depth spike (Phase 8), auth, persistent history, production book storage

- [ ] **T2** `[AGENT]` Create submission `.zip`
  - **Output:** `book-publishing-company-submission.zip` at the workspace root, containing the full project minus secrets and build artefacts
  - **Complexity:** Lightweight
  - **Depends on:** T1
  - **Done when:**
    - Archive created with `zip -r` from the workspace root
    - Excludes confirmed absent: `.env`, `node_modules/` (all depths), `__pycache__/` (all depths), `data/chroma/` (ChromaDB volume data)
    - `unzip -l book-publishing-company-submission.zip | grep -E '\.env$|node_modules|__pycache__|data/chroma'` returns empty
    - Archive contains `book-publishing-company/README.md`, `docker-compose.yml`, `backend/`, `frontend/`, `books shared/`

- [ ] **T3** `[MANUAL]` Review README and verify zip integrity
  - **Output:** Signed-off README and confirmed deliverable zip
  - **Complexity:** Lightweight
  - **Depends on:** T1, T2
  - **Done when:**
    - README reads clearly to someone unfamiliar with the project
    - `.zip` extracted to a temp directory; `docker compose up --build` starts successfully from it
    - No `.env` or chroma data found in the extracted tree

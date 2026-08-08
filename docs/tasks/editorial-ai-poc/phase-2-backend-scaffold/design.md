---
name: phase-2-backend-scaffold
plan: editorial-ai-poc
phase: "phase-2"
type: story
status: pending
---

# Backend Scaffold — Design

## Output

A `docker-compose.yml` at the project root and a `backend/` directory with Dockerfile, pinned `requirements.txt`, and Python package structure (`__init__.py` markers); `docker build ./backend` succeeds with no application code yet.

## Context

Phase 2 creates the structural skeleton that every later phase builds into. Nothing is functional at this stage — the goal is a buildable, correctly-structured foundation that future agents can assume exists.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) §6 (Infrastructure Strategy) and §7 (Directory Structure)

## Decisions inherited from the plan

| Decision | Source |
|---|---|
| Python 3.12 slim base image for backend | plan §7 checklist |
| `requirements.txt` pinned to exact minor versions (e.g. `fastapi==0.115.*`) | plan §4 Key Python dependencies |
| `chromadb==1.5.*` (NOT `0.6.*`) — telemetry bug in 0.6.x produces log noise | plan §4 "Pin chromadb==1.5.*" |
| One `chroma_data` named Docker volume mounted at `/app/data/chroma` | plan §6 docker-compose structure |
| Backend health check: `curl -f http://localhost:8000/api/health` | plan §6 docker-compose structure |
| Frontend service depends on backend (`depends_on: [backend]`) | plan §6 docker-compose structure |
| Books (`little_women.html`, `pride_prejudice.html`) are `COPY`'d into the backend image at build time, sourced from `books shared/` | plan §6 "Books inside the Docker image" |
| `ragas` and `datasets` are Phase 8 only — include in requirements but clearly commented as deferred | plan §4 Key Python dependencies |

## Story-local design

**`__init__.py` content:** empty files. The packages (`api`, `api/routes`, `core`) have no shared init logic at this stage — any module-level setup (client singletons, lifespan hooks) lives in Phase 4.

**`backend/Dockerfile` CMD:** `uvicorn main:app --host 0.0.0.0 --port 8000`. At Phase 2 `main.py` does not exist yet, so the image will build but the container will fail to start — that is expected and correct. Phase 4 writes `main.py`.

**Non-root user:** the Dockerfile SHOULD create a non-root user (`appuser`) and run uvicorn under it. POC does not require it for the demo, but it costs nothing to add and avoids a bad look for an evaluation submission.

**`books shared/` path has a space.** The `COPY` instruction in the Dockerfile must quote or escape it: `COPY ["books shared/", "/app/books/"]`. Inside the container, the books live at `/app/books/little_women.html` and `/app/books/pride_prejudice.html` — no space in the in-container path.

**Vite proxy config is Phase 6, not here.** `docker-compose.yml` wires the services correctly (backend on `8000`, frontend on `3000`); the `/api` proxy from frontend to backend is added to `vite.config.js` in Phase 6.

## Main files to change

- `book-publishing-company/docker-compose.yml` — create: backend + frontend services + chroma_data volume
- `book-publishing-company/backend/Dockerfile` — create: Python 3.12 slim, pip install requirements, COPY books, non-root user, expose 8000
- `book-publishing-company/backend/requirements.txt` — create: pinned versions from plan §4
- `book-publishing-company/backend/__init__.py` — create: empty
- `book-publishing-company/backend/api/__init__.py` — create: empty
- `book-publishing-company/backend/api/routes/__init__.py` — create: empty
- `book-publishing-company/backend/core/__init__.py` — create: empty

## Acceptance criteria

- [ ] `docker-compose.yml` exists at project root with `backend`, `frontend` services and `chroma_data` volume
- [ ] `backend/Dockerfile` uses `python:3.12-slim` base and installs `requirements.txt`
- [ ] `backend/requirements.txt` pins all dependencies listed in plan §4 (fastapi, uvicorn, openai, chromadb 1.5.*, beautifulsoup4, lxml, python-dotenv, ragas, datasets)
- [ ] `COPY ["books shared/", "/app/books/"]` in Dockerfile correctly handles the directory name with a space
- [ ] `backend/api/__init__.py`, `backend/api/routes/__init__.py`, `backend/core/__init__.py` all exist (empty)
- [ ] `docker build ./backend` exits 0 from the `book-publishing-company/` directory

## Out of scope

- `main.py`, `ingest.py`, and all `api/` and `core/` module files — Phase 3 and 4
- Vite proxy config — Phase 6
- `.env` values — already exists; not touched here
- CI/CD — out of scope for entire POC (plan §8)

## Risks

- **`books shared/` space in COPY path.** Docker's `COPY` instruction with a space in the source path requires the JSON array form; the string form will misparse. Medium likelihood of a first-draft error — the acceptance criterion explicitly checks this.
- **`chromadb==1.5.*` resolution.** pip resolves `1.5.*` to latest patch at build time. If PyPI has a broken `1.5.x` release, the build fails. Low probability; if it occurs, pin to the last known-good patch (e.g. `chromadb==1.5.9`).

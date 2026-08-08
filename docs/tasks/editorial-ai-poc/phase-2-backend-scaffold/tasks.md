---
name: phase-2-backend-scaffold
plan: editorial-ai-poc
phase: "phase-2"
type: tasks
---

# Backend Scaffold — Tasks

Dependency-ordered. Every task is tagged `[MANUAL]` or `[AGENT]` and states its output.

## Tasks

- [x] **T1** `[AGENT]` Write `docker-compose.yml`
  - **Output:** `book-publishing-company/docker-compose.yml` — two services (`backend` on `8000`, `frontend` on `3000`), `chroma_data` named volume, backend health check, `depends_on` on frontend
  - **Complexity:** Standard
  - **Depends on:** —
  - **Done when:** file exists, contains both service definitions, defines `chroma_data` volume, backend `healthcheck` uses `curl -f http://localhost:8000/api/health`, and frontend `depends_on: [backend]`

- [x] **T2** `[AGENT]` Create backend Python package structure
  - **Output:** `backend/api/__init__.py`, `backend/api/routes/__init__.py`, `backend/core/__init__.py` — all empty files, directories created
  - **Complexity:** Lightweight
  - **Depends on:** —
  - **Done when:** all three `__init__.py` files exist (empty); `backend/api/routes/` and `backend/core/` directories exist

- [x] **T3** `[AGENT]` Write `backend/requirements.txt`
  - **Output:** `book-publishing-company/backend/requirements.txt` — all Python dependencies pinned to minor versions per plan §4
  - **Complexity:** Lightweight
  - **Depends on:** —
  - **Done when:** file exists and contains: `fastapi==0.115.*`, `uvicorn[standard]==0.32.*`, `openai==1.57.*`, `chromadb==1.5.*`, `beautifulsoup4==4.13.*`, `lxml==5.3.*`, `python-dotenv==1.0.*`; Phase 8 deps (`ragas==0.2.*`, `datasets==3.*`) present but commented with a note

- [x] **T4** `[AGENT]` Write `backend/Dockerfile`
  - **Output:** `book-publishing-company/backend/Dockerfile` — Python 3.12 slim image, pip install from requirements, COPY books (handling the space in `books shared/`), non-root user, expose 8000, CMD uvicorn
  - **Complexity:** Standard
  - **Depends on:** T2, T3
  - **Done when:** Dockerfile uses `python:3.12-slim`, uses JSON array form for the books COPY (`COPY ["books shared/", "/app/books/"]`), creates a non-root user, `EXPOSE 8000`, `CMD` launches uvicorn on `0.0.0.0:8000`; `docker build ./backend` from `book-publishing-company/` exits 0

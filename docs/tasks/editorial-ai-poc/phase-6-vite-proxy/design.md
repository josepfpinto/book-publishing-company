---
name: phase-6-vite-proxy
plan: editorial-ai-poc
phase: "phase-6"
type: story
status: pending
---

# Vite Proxy + Smoke Tests — Design

## Output

`frontend/vite.config.js` proxies `/api` to the backend Docker service, and manual smoke tests (including deferred T4 + T5 from Phase 5) confirm the stack runs end-to-end.

## Context

The frontend calls the relative path `/api/chat` (no origin prefix). In the Docker Compose setup the frontend container runs the Vite dev server (`npx vite --host 0.0.0.0 --port 3000`), so a `server.proxy` entry in `vite.config.js` routes those relative calls to `http://backend:8000` — the backend service name as resolved inside the Docker network. Without this the browser-issued `fetch('/api/chat')` hits the Vite server itself and returns 404.

Deferred tasks T4 (visual layout verification) and T5 (source card width / no-overflow) from Phase 5 Story 2 are folded into the smoke test here, as they require a live backend with real streaming.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) § Phase 6 §6.1

## Decisions inherited from the plan

| Decision | Source |
| --- | --- |
| Proxy target is `http://backend:8000` (Docker Compose service name, not `localhost`) | plan §6.1 |
| Frontend Dockerfile runs Vite dev server — proxy applies in Docker | plan §6 Infrastructure |
| Smoke test includes scope-switch scenario (§4 history-scope defect) | plan §6.1 |
| T4 (streaming + visual) and T5 (source card width) verified here, not in Phase 5 | plan §6.1 note |

## Story-local design

**Proxy config shape** (Vite `server.proxy`):

```js
server: {
  proxy: {
    '/api': 'http://backend:8000',
  },
},
```

A bare string target instructs Vite to forward matching paths verbatim — no rewriting needed since the backend mounts routes at `/api/...`.

**Local dev note (out of scope for this POC):** the target `http://backend:8000` only resolves inside Docker. Developers running Vite on the host against a local backend would need `http://localhost:8000`. The POC workflow is `docker compose up --build` only; a dual-target env-var approach is deferred.

## Main files to change

- `frontend/vite.config.js` — add `server.proxy` block

## Acceptance criteria

- [ ] `docker compose up --build` starts without errors; both containers reach healthy state
- [ ] `GET http://localhost:3000/` renders the app (WelcomeState with book toggle and suggested questions)
- [ ] Sending "What is the plot of Little Women?" returns a streaming answer with ≥1 source card (single-book path)
- [ ] Sending a cross-book question under "Both Books" returns an answer drawing on both books
- [ ] Scope-switch scenario: cross-book question → switch toggle to "Little Women" → P&P follow-up → model stays inside Little Women scope or explicitly declines
- [ ] Source cards: 3 cards share column width equally (`flex: 1 1 0`), no horizontal overflow, no card clipped **(T5)**
- [ ] Tokens appear progressively during streaming; source cards appear after stream completes **(T4)**
- [ ] Fresh reload returns to WelcomeState with toggle on "Both Books" **(T4)**
- [ ] Visual layout matches all 7 design screenshots **(T4)**

## Out of scope

- Host-only Vite dev setup (non-Docker local development)
- CI-automated integration tests — manual smoke test is the gate for this POC

## Risks

- **Docker build cache:** a stale frontend layer may serve the old `vite.config.js`. `--build` forces a rebuild; if the proxy still appears absent, `docker compose build --no-cache frontend`.
- **Backend health check timing:** `frontend` depends on `backend` with `condition: service_healthy`. If ChromaDB init is slow on first run, the frontend may wait. Not a code bug — just takes longer on a cold start.

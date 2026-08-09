---
name: phase-6-vite-proxy
plan: editorial-ai-poc
phase: "phase-6"
type: tasks
---

# Vite Proxy + Smoke Tests — Tasks

Dependency-ordered. Every task is tagged `[MANUAL]` or `[AGENT]` and states its output.

## Tasks

- [x] **T1** `[AGENT]` Add Vite proxy config to `vite.config.js`
  - **Output:** `frontend/vite.config.js` has a `server.proxy` block forwarding `/api` to `http://backend:8000`
  - **Complexity:** Lightweight
  - **Depends on:** —
  - **Done when:**
    - `vite.config.js` exports a config with `server: { proxy: { '/api': 'http://backend:8000' } }`
    - Existing `plugins: [react()]` entry is preserved

- [x] **T2** `[MANUAL]` Verify content-filter error surface in the running UI
  - **Output:** Confirmation that a content-filtered request shows an error card rather than a hung/blank stream
  - **Complexity:** Lightweight
  - **Depends on:** T1, phase-6-sse-hardening merged
  - **Done when:** Sending a message that triggers Azure content policy returns a visible error message in the chat UI within a reasonable timeout; no spinner freeze observed

- [x] **T3** `[MANUAL]` Run full stack and execute smoke test suite (includes deferred T4 + T5 from Phase 5)
  - **Output:** Manual sign-off that the full stack works end-to-end against all 7 design screenshots with correct streaming, source cards, and scope switching
  - **Complexity:** Standard
  - **Depends on:** T1, T2
  - **Done when:** All of the following pass:
    - `docker compose up --build` starts cleanly; both containers healthy
    - "What is the plot of Little Women?" returns a streaming answer with source cards
    - Cross-book question under "Both Books" returns an answer drawing on both books
    - Scope-switch scenario: cross-book question → toggle to "Little Women" → P&P follow-up stays scoped or model declines (§4 history-scope fix verified)
    - 3 source cards share column width equally, no overflow, no clipping **(T5)**
    - Tokens appear progressively; source cards appear after stream completes **(T4)**
    - Fresh reload → WelcomeState with toggle on "Both Books" **(T4)**
    - Visual layout matches all 7 design screenshots **(T4)**

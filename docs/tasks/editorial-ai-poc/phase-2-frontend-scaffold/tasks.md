---
name: phase-2-frontend-scaffold
plan: editorial-ai-poc
phase: "phase-2"
type: tasks
---

# Frontend Scaffold — Tasks

Dependency-ordered. Every task is tagged `[MANUAL]` or `[AGENT]` and states its output.

## Tasks

- [x] **T1** `[AGENT]` Write `frontend/package.json`
  - **Output:** `book-publishing-company/frontend/package.json` — React 18 + Vite 5 deps, `dev` / `build` / `preview` scripts
  - **Complexity:** Standard
  - **Depends on:** —
  - **Done when:** file declares `react` and `react-dom` at `^18.x`, `vite` and `@vitejs/plugin-react` as devDependencies, and includes `"dev": "vite"`, `"build": "vite build"`, `"preview": "vite preview"` scripts

- [x] **T2** `[AGENT]` Write `frontend/vite.config.js`
  - **Output:** `book-publishing-company/frontend/vite.config.js` — minimal Vite config with React plugin only
  - **Complexity:** Lightweight
  - **Depends on:** T1
  - **Done when:** file imports `react` from `@vitejs/plugin-react`, exports a `defineConfig` with the plugin — no proxy (Phase 6), no aliases

- [x] **T3** `[AGENT]` Write `frontend/index.html`
  - **Output:** `book-publishing-company/frontend/index.html` — Vite HTML entrypoint
  - **Complexity:** Lightweight
  - **Depends on:** —
  - **Done when:** file has `<title>Editorial AI</title>`, `<div id="root"></div>`, and `<script type="module" src="/src/main.jsx"></script>`

- [x] **T4** `[AGENT]` Create `frontend/src/` structure with stubs
  - **Output:** `frontend/src/main.jsx` (React 18 createRoot mount), `frontend/src/App.jsx` (minimal valid JSX), and `.gitkeep` files in `src/lib/`, `src/styles/`, `src/components/`
  - **Complexity:** Lightweight
  - **Depends on:** —
  - **Done when:** `main.jsx` uses `ReactDOM.createRoot` (NOT `ReactDOM.render`), `App.jsx` is valid JSX returning at least one element; `src/lib/`, `src/styles/`, `src/components/` directories exist

- [x] **T5** `[AGENT]` Write `frontend/Dockerfile`
  - **Output:** `book-publishing-company/frontend/Dockerfile` — Node 18 alpine, npm install, expose 3000, CMD vite dev
  - **Complexity:** Standard
  - **Depends on:** T1, T4
  - **Done when:** Dockerfile uses `node:18-alpine`, copies `package.json` and installs, copies `src/` and config files, `EXPOSE 3000`, CMD is `["npx", "vite", "--host", "0.0.0.0", "--port", "3000"]` (or equivalent); `docker build ./frontend` exits 0

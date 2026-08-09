---
name: phase-5-components
plan: editorial-ai-poc
phase: "phase-5"
type: story
status: pending
---

# Phase 5 · Story 1: Design System + Presentational Components — Design

## Output

All presentational components (AppHeader, BookToggle, WelcomeState, UserMessage, AssistantMessage, SourceList, SourceCard, ChatInput), the design token stylesheet (`globals.css`), and the SSE client utility (`streamChat.js`) exist and are independently correct — renderable with mock props, or (for `streamChat.js`) executable in isolation.

## Context

Phase 5 builds the complete React frontend from the bare Vite scaffold. This story handles everything that has no dependency on App-level state: the design foundation (tokens, fonts, CSS reset) and all leaf components that receive their data as props. Story 2 (`phase-5-app-composition`) assembles these into the full stateful app.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) §3, §5

## Decisions inherited from the plan

| Decision | Source |
|---|---|
| Design tokens: `--bg #F9F9F7`, `--ink #181928`, `--accent #CB7026`, `--surface #FFFFFF`, `--surface-subtle #FCFCFB`, `--hairline #E4E2DC` — pixel-sampled, not prompt values | plan §3 token table |
| Typography: Inter (body/UI) + one monospace (micro-labels), both via Google Fonts | plan §3 decisions |
| No component library — plain CSS + CSS custom properties throughout | plan §3 decisions |
| BookToggle: 3-way segmented control, **navy `#181928`** active fill (not amber), open-book SVG glyph per segment | plan §3 design override #1, #7 |
| AssistantMessage: amber left rule + mono `AI` label; **no bubble, no shadow** (biggest structural difference from prompt) | plan §3 design override #2 |
| UserMessage: right-aligned white card, hairline border, mono timestamp bottom-right; ~55% column width | plan §3 design override #3 |
| Header: two-line — mono eyebrow + `Editorial AI` + `VOL. 01` right-aligned (not `VOL. 01 / 2024`) | plan §3 override #4, defect B fix |
| SourceCard: equal-width `flex: 1 1 0`, book title + chapter line + italic excerpt; no `SOURCE 01/03` counter | plan §3 defect A fix, §5 |
| SourceCard chapter line: always starts `Chapter {n}`; dash-title only if `chapter_title != "Chapter {n}"`; page appended if present | plan §4 Citation schema, §5 |
| SourceCard excerpt: read from `excerpt` metadata field; italic, typographic quotes; clamp at 4 lines (CSS, no length cap) | plan §4 Excerpt rule, §5 |
| ChatInput: two distinct disabled conditions — (1) empty/whitespace-only → send disabled; (2) isLoading → both disabled + dimmed | plan §5 disabled logic table |
| `streamChat.js`: `fetch` POST + `response.body.pipeThrough(TextDecoderStream).getReader()` + `buffer.split("\n\n") / pop()` partial-frame pattern | plan §5 streaming pseudocode |
| `EventSource` is explicitly ruled out — POST with JSON body is incompatible with EventSource GET | plan §5 |
| Desktop-first — no responsive/mobile work | plan §3 decisions |
| Session fully transient — no localStorage | plan §3 decisions |

## Story-local design

**Monospace font:** `Space Mono` (Google Fonts). Named in the plan as "one monospace" without pinning the face. `Space Mono` has the tight letterspacing and editorial tone the micro-labels need. Override in `[MANUAL]` review if a different face is preferred.

**Suggested-question copy (WelcomeState):** Three buttons. Proposed strings aligned with the plan's canonical copy:
1. `"What motivates Jo March to refuse Laurie's proposal?"`
2. `"How does economic status shape the Bennet daughters' choices?"`
3. `"Compare the opening lines of both novels."`
Override during `[MANUAL]` review step in Story 2.

**CSS organisation:** All styles in `src/styles/globals.css`. Components use `className` strings that map to selectors defined globally. No CSS modules, no per-component files — the plan's §7 directory structure lists only `globals.css`.

**Google Fonts loading:** `@import` at the top of `globals.css` (Vite bundles CSS; the import fires at load time). No `<link>` tag added to `index.html`.

**Pulsing-dots animation:** Three `<span>` elements inside the AssistantMessage bubble while `isLoading`. CSS `@keyframes` pulse defined in `globals.css`. Dots disappear when streaming text starts.

**WelcomeState greeting:** Mixed italic/roman display line per plan §3 override #9 — _"Ready to answer questions about"_ **Little Women** _"and"_ **Pride & Prejudice.** Not a chat bubble; rendered as a standalone display element.

## Main files to change

- `frontend/src/styles/globals.css` — create: CSS tokens, Google Fonts @import, base type scale, reusable class utilities
- `frontend/src/lib/streamChat.js` — create: SSE fetch + frame parser + AbortController
- `frontend/src/components/AppHeader.jsx` + CSS — create
- `frontend/src/components/BookToggle.jsx` + CSS — create
- `frontend/src/components/WelcomeState.jsx` + CSS — create
- `frontend/src/components/UserMessage.jsx` + CSS — create
- `frontend/src/components/AssistantMessage.jsx` + CSS — create
- `frontend/src/components/SourceList.jsx` + `SourceCard.jsx` + CSS — create
- `frontend/src/components/ChatInput.jsx` + CSS — create

## Acceptance criteria

- [ ] `globals.css` defines all six sampled design tokens as CSS custom properties on `:root`; Inter and Space Mono load from Google Fonts via `@import`
- [ ] BookToggle renders three segments; the active segment has `--ink` fill and white text; inactive segments have transparent fill and `--ink` text; clicking a segment calls `onSelect` with the correct `book_id`
- [ ] Each BookToggle segment contains an inline SVG book glyph that inherits `currentColor`
- [ ] AssistantMessage renders with an amber left rule (`--accent`) and a mono `AI` label; no bubble, no box-shadow
- [ ] AssistantMessage shows three pulsing dots when `isLoading === true` and streaming text when `isLoading === false`
- [ ] UserMessage is right-aligned at ~55% column width with a white card and `--hairline` border; timestamp uses Space Mono
- [ ] SourceCard chapter line: shows `Chapter {n}` always; appends `— {title}` only when `chapter_title !== "Chapter {n}"`; appends page range when present
- [ ] SourceCard excerpt is italic, wrapped in typographic quotes, clamped at 4 lines; never cuts mid-word (reads the pre-computed `excerpt` field)
- [ ] Three SourceCards in a row use `flex: 1 1 0` and fit within the column without overflow or horizontal scroll
- [ ] ChatInput send button uses `--accent` fill when enabled; `--hairline` fill when disabled (empty input); both textarea and button are dimmed when `isLoading`
- [ ] `streamChat.js` correctly handles an SSE payload split across two network chunks (partial-frame buffer pattern); does not throw on a half-received `data:` line
- [ ] `streamChat.js` supports `AbortController` cancellation via a `signal` option
- [ ] Header shows mono eyebrow + "Editorial AI" + "VOL. 01" (no year); hairline bottom border

## Out of scope

- App-level state (`messages[]`, `currentBookContext`, `isLoading`, `activeStreamId`) — Story 2
- ChatPanel and MessageList — Story 2
- App.jsx full implementation — Story 2
- Manual visual verification against screenshots — Story 2
- Vite proxy config — Phase 6 §6.1
- SSE error-contract hardening in the backend — Phase 6 §6.0
- Mobile/responsive layout — deferred per plan §8
- Per-component CSS files / CSS modules — explicitly not chosen

## Risks

- **Space Mono may not match the evaluator's expectation** — the plan does not name the mono face; any Google Fonts mono is valid. The [MANUAL] review in Story 2 is the gate.
- **Google Fonts network dependency** — `@import` requires internet at load time in both dev and the Docker container. The frontend Dockerfile will need to `npm run build` (which bundles CSS), so fonts are fetched at build time, not runtime. In dev, the machine needs internet.
- **SSE partial-frame logic** — the `buffer.split("\n\n") / pop()` pattern is explicitly flagged in the plan as "easy to get wrong." The acceptance criterion requires a test against a split payload.

---
name: phase-5-components
plan: editorial-ai-poc
phase: "phase-5"
type: tasks
---

# Phase 5 · Story 1: Design System + Presentational Components — Tasks

Dependency-ordered. Every task is tagged `[MANUAL]` or `[AGENT]` and states its output.

## Tasks

- [x] **T1** `[AGENT]` Write `src/styles/globals.css`
  - **Output:** CSS file exists with all six sampled design tokens as CSS custom properties on `:root`; Google Fonts `@import` for Inter (400, 500) and Space Mono (400, 700); base type-scale utilities (body 15px, chapter names 13px bold, excerpts 12px, header app name 18px medium, micro-labels 11px letterspaced); `box-sizing: border-box` reset; no component-specific rules yet
  - **Complexity:** Standard
  - **Depends on:** —
  - **Done when:** `npm run dev` serves a page where the CSS custom properties are visible in DevTools and Google Fonts resolve in the network tab

- [x] **T2** `[AGENT]` Write `src/lib/streamChat.js`
  - **Output:** Module exports a single `streamChat({ bookId, message, history, onToken, onSources, onError, onDone, signal })` function. Sends `POST /api/chat` with JSON body; reads the `ReadableStream` via `pipeThrough(new TextDecoderStream()).getReader()`; applies the `buffer.split("\n\n") / pop()` partial-frame pattern; dispatches `onToken(token)`, `onSources(sources)`, `onError(message)`, `onDone()` callbacks per event type. Accepts an `AbortController` signal for cancellation.
  - **Complexity:** Full — the partial-frame buffer is the critical correctness requirement; a network chunk split mid-`data:` line must not throw
  - **Depends on:** —
  - **Done when:** manual test against a mock SSE response split across two chunks produces the correct sequence of callbacks without errors; `AbortController` abort cancels the stream without throwing an uncaught rejection

- [x] **T3** `[AGENT]` Write `src/components/AppHeader.jsx`
  - **Output:** React component renders a `<header>` with: (1) a mono-font eyebrow line `A READING COMPANION FOR EDITORS`; (2) `Editorial AI` in 18px medium sans-serif; (3) `VOL. 01` right-aligned in mono; all on one bar with a `--hairline` bottom border and `--bg` background. No props required.
  - **Complexity:** Lightweight
  - **Depends on:** T1 (uses CSS tokens)
  - **Done when:** component renders in a dev harness matching the header shown in screenshots 1–7

- [x] **T4** `[AGENT]` Write `src/components/BookToggle.jsx`
  - **Output:** React component accepts `{ selected, onSelect }` props. Renders a 3-segment pill: `little_women` / `both` / `pride_prejudice`. Active segment: `--ink` background, white text. Inactive: transparent, `--ink` text. Thin `--ink` border on the pill. Each segment contains an inline SVG open-book glyph using `currentColor`. Clicking calls `onSelect(bookId)`. Canonical UI labels: `Little Women` · `Both Books` · `Pride & Prejudice`.
  - **Complexity:** Standard — inline SVG, active-fill CSS, three-state logic
  - **Depends on:** T1
  - **Done when:** all three segments render; clicking each calls `onSelect` with the correct `book_id`; active fill and inactive states are visually correct

- [x] **T5** `[AGENT]` Write `src/components/WelcomeState.jsx`
  - **Output:** React component accepts `{ onSubmit }` prop. Renders: (1) a centered display line — italic _"Ready to answer questions about"_ then bold `Little Women` then italic _"and"_ then bold `Pride & Prejudice.`; (2) `OR TRY ASKING` mono divider; (3) three suggested-question buttons (strings from design.md §Story-local design) — clicking any populates the input and submits immediately via `onSubmit(questionString)`.
  - **Complexity:** Lightweight
  - **Depends on:** T1
  - **Done when:** all three buttons render; clicking one calls `onSubmit` with the button's question string

- [x] **T6** `[AGENT]` Write `src/components/UserMessage.jsx`
  - **Output:** React component accepts `{ content, timestamp }` props. Renders right-aligned white card at ~55% column width, `--hairline` border, rounded corners. `content` in `--ink` body text. `timestamp` in Space Mono 11px at bottom-right of the card. No avatar.
  - **Complexity:** Lightweight
  - **Depends on:** T1
  - **Done when:** component renders with correct alignment, width, and mono timestamp

- [x] **T7** `[AGENT]` Write `src/components/AssistantMessage.jsx`
  - **Output:** React component accepts `{ content, isStreaming }` props. Layout: 2px amber (`--accent`) left rule; mono `AI` label + `timestamp` on the same line as the rule (small, letterspaced); body text runs full column width (no bubble, no shadow). When `isStreaming === true`: shows three animated pulsing dots (`@keyframes` pulse in globals.css) instead of body text. When `isStreaming === false`: renders `content` as body text.
  - **Complexity:** Standard — two visual states, CSS animation, no-bubble layout
  - **Depends on:** T1
  - **Done when:** pulsing dots show when `isStreaming=true`; full text shows when `false`; amber left rule and no-bubble layout match screenshots 4, 5, 7

- [x] **T8** `[AGENT]` Write `src/components/SourceList.jsx` and `src/components/SourceCard.jsx`
  - **Output:** `SourceList` accepts `{ sources }` array prop; renders up to 3 `SourceCard` components in a `display: flex` row where each card is `flex: 1 1 0` — equal-width thirds with no overflow and no horizontal scroll. `SourceCard` accepts one source object from the SSE `sources` payload and renders: (1) book title in small amber uppercase Space Mono; (2) chapter line always starting `Chapter {n}`, appending `— {chapter_title}` only when `chapter_title !== "Chapter {n}"`, appending `· p. {page_start}` / `· pp. {page_start}–{page_end}` when page data is present; (3) `excerpt` in italic typographic quotes, clamped at 4 lines via `-webkit-line-clamp`. White background, `--hairline` border, rounded corners.
  - **Complexity:** Standard — chapter-line formatting logic, flex equal-width layout, excerpt clamp
  - **Depends on:** T1
  - **Done when:** 3 cards fit within the column without overflow; chapter line renders all four canonical forms (LW full, P&P with pages, P&P base, base case); excerpt clamps at 4 lines

- [x] **T9** `[AGENT]` Write `src/components/ChatInput.jsx`
  - **Output:** React component accepts `{ onSubmit, isLoading }` props. Renders: (1) a `<textarea>` that auto-expands from 1 to 3 lines then scrolls; placeholder `Ask something about the book…`; (2) a send `<button>` to the right. Disabled logic: empty/whitespace-only input → button disabled with `--hairline` fill, textarea enabled; `isLoading` → both disabled and textarea dimmed (`opacity: 0.5`). Idle with non-whitespace → button enabled with `--accent` fill. Submits on button click or `Enter` (not `Shift+Enter`).
  - **Complexity:** Standard — auto-expanding textarea, two distinct disabled conditions, keyboard handling
  - **Depends on:** T1
  - **Done when:** textarea expands to 3 lines then scrolls; both disabled conditions produce the correct visual state; `Enter` submits; `Shift+Enter` adds a newline

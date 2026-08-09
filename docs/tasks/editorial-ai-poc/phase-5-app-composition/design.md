---
name: phase-5-app-composition
plan: editorial-ai-poc
phase: "phase-5"
type: story
status: pending
---

# Phase 5 · Story 2: App Composition — Design

## Output

A complete, functional React chat app: `ChatPanel`, `MessageList`, and `App.jsx` are wired with full state management; streaming tokens accumulate in real time; source cards appear after each AI response; book toggle switches context; manual visual verification against all 7 design screenshots passes.

## Context

This story assembles the stateful shell around the presentational components from Story 1 (`phase-5-components`). All leaf components exist; this story wires them with React state, integrates `streamChat.js`, and performs the manual visual review.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) §5

## Decisions inherited from the plan

| Decision | Source |
|---|---|
| `App` owns `messages[]`, `currentBookContext`, `isLoading`, `activeStreamId` | plan §5 component tree |
| `currentBookContext` is read at submit time and **frozen** onto the message object as `message.bookContext` — switching the toggle mid-stream cannot retarget an in-flight query | plan §5 |
| `MessageList` auto-scrolls to bottom during streaming | plan §5 component tree |
| `CONVERSATION` mono divider renders above the first turn (not in WelcomeState) | plan §3 override #6 |
| Hairline rules between turns | plan §3 override #6 |
| WelcomeState renders only when `messages.length === 0` | plan §5 component tree |
| Suggested-question buttons call `onSubmit(question)` → populate input AND submit immediately (no extra keystroke) | plan §5 WelcomeState / SuggestedQuestion spec |
| Streaming: `AbortController` abort on new message or unmount; `activeStreamId` tracks in-flight request | plan §5 |
| Default book context: `both` (both books selected on load) | plan §5 — fresh reload returns to WelcomeState with toggle on "Both Books" |
| `isLoading` true from submit → false on `onDone()` callback | plan §5 |
| Session fully transient — no localStorage | plan §3 decisions |

## Story-local design

**`App` state shape:**
```js
messages: [
  {
    id: string,           // crypto.randomUUID() or Date.now() string
    role: "user" | "assistant",
    content: string,      // accumulates tokens for assistant; full text for user
    bookContext: string,  // book_id frozen at submit time
    timestamp: string,    // "HH:MM" generated client-side
    sources: [],          // filled on onSources() callback
    isStreaming: boolean, // true while tokens arriving
  }
]
currentBookContext: "both" | "little_women" | "pride_prejudice"  // default "both"
isLoading: boolean
activeStreamId: string | null
```

**Message list auto-scroll:** use a `ref` on a bottom sentinel `<div>`; call `scrollIntoView({ behavior: "smooth" })` in a `useEffect` that runs whenever `messages` changes or the last message's `content` changes.

**`CONVERSATION` divider:** rendered once, above the first message, by `MessageList` when `messages.length > 0`. Uses Space Mono, letterspaced, `--hairline` rules on each side.

**Hairline between turns:** a `<hr>` or a `<div>` with `border-top: 1px solid var(--hairline)` between each `UserMessage` / `AssistantMessage` pair, not between every individual element.

**ChatPanel layout:** `display: flex; flex-direction: column; flex: 1`. MessageList takes `flex: 1; overflow-y: auto`. ChatInput is pinned at the bottom (not `position: fixed` — just the last flex child).

**Error display:** when `onError(msg)` fires, append an assistant message with `content: msg` and `isStreaming: false`. No separate error UI component needed.

## Main files to change

- `frontend/src/components/ChatPanel.jsx` — create: CONVERSATION divider + MessageList + ChatInput composition + submit handler
- `frontend/src/components/MessageList.jsx` — create: maps `messages[]` to UserMessage / AssistantMessage + SourceList; CONVERSATION divider; auto-scroll sentinel
- `frontend/src/App.jsx` — rewrite stub: owns all state, renders AppHeader + BookToggle + ChatPanel, calls streamChat

## Acceptance criteria

- [ ] On load: WelcomeState is visible, BookToggle defaults to "Both Books", no messages
- [ ] Clicking a suggested question in WelcomeState submits it immediately (no extra keystroke); WelcomeState disappears and a UserMessage appears
- [ ] Switching the BookToggle mid-stream does not retarget the in-flight request
- [ ] While streaming: `AssistantMessage` shows pulsing dots, then transitions to streaming text as tokens arrive; textarea and send button are disabled
- [ ] After streaming completes: source cards appear below the AssistantMessage in a 3-card flex row that does not overflow the column
- [ ] `CONVERSATION` mono divider appears above the first message; hairline rules appear between turns
- [ ] MessageList auto-scrolls to the bottom as new tokens arrive
- [ ] Fresh page reload returns to WelcomeState with toggle on "Both Books"
- [ ] Visual layout matches all 7 design screenshots when running at `http://localhost:3000` (manual gate)
- [ ] Source row does not clip card 3 at any window width ≥ the column's max-width (manual gate)

## Out of scope

- Vite proxy config — Phase 6 §6.1 (Phase 5 verification runs `npm run dev` and calls the backend at its full URL if needed, or uses WelcomeState static state for layout checks)
- SSE error-contract hardening in the backend — Phase 6 §6.0
- End-to-end Docker smoke tests — Phase 6 §6.1
- RAG spike — Phase 8
- Mobile/responsive layout — deferred

## Risks

- **Auto-scroll fighting user scroll** — if the user scrolls up while streaming, auto-scrolling back to the bottom is jarring. Acceptable for a POC; a production fix would detect user scroll and pause auto-scroll.
- **Font flash (FOUT)** — Google Fonts load after the first render. Space Mono may flash to a fallback briefly. Not a concern for a local demo; add `font-display: swap` in the `@import` URL if needed.
- **`crypto.randomUUID()` availability** — available in all modern browsers and in Node 18+ (used in Vite dev server context). Safe for this POC.

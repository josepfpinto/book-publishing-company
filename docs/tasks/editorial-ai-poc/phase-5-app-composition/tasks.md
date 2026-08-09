---
name: phase-5-app-composition
plan: editorial-ai-poc
phase: "phase-5"
type: tasks
---

# Phase 5 · Story 2: App Composition — Tasks

Dependency-ordered. Every task is tagged `[MANUAL]` or `[AGENT]` and states its output.

## Tasks

- [x] **T1** `[AGENT]` Write `src/components/ChatPanel.jsx`
  - **Output:** React component accepts `{ messages, isLoading, onSubmit }` props. Renders: (1) `CONVERSATION` mono divider (visible only when `messages.length > 0`); (2) `<MessageList messages={messages} isLoading={isLoading} />`; (3) `<ChatInput onSubmit={onSubmit} isLoading={isLoading} />` pinned at the bottom. No independent state — all data flows from App.
  - **Complexity:** Standard
  - **Depends on:** Story 1 (MessageList and ChatInput from phase-5-components)
  - **Done when:** component renders the divider, message list, and input in the correct vertical order; ChatInput stays at the bottom while MessageList scrolls

- [x] **T2** `[AGENT]` Write `src/components/MessageList.jsx`
  - **Output:** React component accepts `{ messages }` prop. Maps each message to `<UserMessage>` or `<AssistantMessage>` + `<SourceList>` (rendered below each completed assistant message). Inserts a `--hairline` divider between turns. Maintains a bottom-sentinel `<div ref>` and calls `scrollIntoView({ behavior: "smooth" })` in a `useEffect` on `messages` changes to auto-scroll during streaming.
  - **Complexity:** Standard — auto-scroll ref, conditional source list rendering
  - **Depends on:** T1; Story 1 components (UserMessage, AssistantMessage, SourceList)
  - **Done when:** new messages and streaming token updates cause the list to scroll to the bottom; SourceList renders below each completed assistant message; dividers appear between turns

- [x] **T3** `[AGENT]` Write `src/App.jsx` (full implementation)
  - **Output:** App owns state as specified in design.md (`messages[]`, `currentBookContext`, `isLoading`, `activeStreamId`). On submit: (a) freeze `currentBookContext` as `message.bookContext`; (b) append UserMessage; (c) append a streaming AssistantMessage placeholder; (d) call `streamChat({ bookId, message, history, onToken, onSources, onError, onDone, signal })`; (e) accumulate tokens into the placeholder's `content`; (f) on `onSources`, set `sources` on the placeholder; (g) on `onDone`, set `isStreaming: false` and clear `isLoading`. BookToggle calls `setCurrentBookContext`. Single-column layout: `<AppHeader>` + `<BookToggle>` + `<ChatPanel>`. Renders `<WelcomeState>` inside ChatPanel when `messages.length === 0`.
  - **Complexity:** Full — state ownership, streaming accumulation, context freeze at submit, abort logic
  - **Depends on:** T1, T2; Story 1 (all components + streamChat)
  - **Done when:** full interaction loop works — submit → stream tokens → sources appear → input re-enables; toggle switch mid-stream does not retarget the in-flight request; page reload returns to WelcomeState

- [ ] **T4** `[MANUAL]` Verify UI in browser at `http://localhost:3000` — side-by-side against all 7 design screenshots
  - **Output:** Sign-off that layout, typography, colors, and interaction states match the Mowgli render
  - **Complexity:** Lightweight
  - **Depends on:** T3
  - **Done when:** all 7 screenshots checked; any mismatches are filed as bugs or accepted as intentional deviations and noted here
  - **DEFERRED to Phase 6:** Vite proxy config (Phase 6 §6.1) required to connect frontend to backend for streaming verification. Visual layout (WelcomeState, BookToggle, CONVERSATION divider, message bubbles) signed off as matching design. Full streaming/source-cards verification deferred.

- [ ] **T5** `[MANUAL]` Verify source card row does not clip at 3 cards
  - **Output:** Confirmation that 3 cards share the column width equally (`flex: 1 1 0`) with no overflow or clipping (§3 defect A fix)
  - **Complexity:** Lightweight
  - **Depends on:** T4
  - **Done when:** source row with 3 cards renders entirely within the column at the standard browser zoom level; no horizontal scrollbar; card 3 is fully visible
  - **DEFERRED to Phase 6:** depends on T4 streaming verification.

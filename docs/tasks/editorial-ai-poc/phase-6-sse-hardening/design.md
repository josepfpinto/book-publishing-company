---
name: phase-6-sse-hardening
plan: editorial-ai-poc
phase: "phase-6"
type: story
status: pending
---

# SSE Error-Contract Hardening — Design

## Output

`backend/api/routes/chat.py` has a complete three-layer error envelope with tests covering all three new error paths.

## Context

Phase 4 shipped a minimal error handler that only catches `openai.BadRequestError` at `.create()` time. Three gaps leave the client hanging on a committed HTTP 200 when errors occur before or during streaming. They must be closed before smoke testing (§6.1) because any transient Azure error during testing is otherwise indistinguishable from a freeze.

Plan: [`editorial-ai-poc.plan.md`](../../editorial-ai-poc.plan.md) § Phase 6 §6.0

## Decisions inherited from the plan

| Decision | Source |
| --- | --- |
| Outer envelope catches all exceptions; yields `{"error": "..."}` then `{"done": true}`; never re-raises (headers committed) | plan §6.0 Gap A |
| `try/except openai.BadRequestError` must cover the iteration loop, not only `.create()` | plan §6.0 Gap B |
| `delta.refusal` → error event with refusal text; `finish_reason == "content_filter"` → error event; both terminate the stream | plan §6.0 Gap C |
| Implementation order: A → B → C (A provides the safety net for B and C) | plan §6.0 |
| Inner `content_filter` guard stays unchanged; non-filter `BadRequestError` bubbles to the outer envelope | plan §6.0 Gap B |

## Story-local design

**Where the outer envelope sits:** the entire body of `generate()` — from `analyze_query` through the final `yield _sse({"done": True})` — is wrapped. The outer `except Exception` catches anything that escapes the inner guards and yields a generic error message (not the raw exception string, which may leak internal detail).

**`generate()` is a synchronous generator** (uses `def`, not `async def`). The `try/except` structure is standard Python generator error handling; no async subtlety applies here.

**Test strategy:** all three gap tests follow the existing pattern in `test_chat.py` — mock external deps via `patch`, drive via `TestClient`, parse SSE frames with `_parse_sse()`. No new test infrastructure needed.

## Main files to change

- `backend/api/routes/chat.py` — add outer envelope (Gap A), expand `BadRequestError` guard to cover iteration loop (Gap B), add `delta.refusal` and `finish_reason` checks in loop (Gap C)
- `backend/tests/test_chat.py` — three new tests (one per gap)

## Acceptance criteria

- [ ] Any exception raised by `analyze_query`, `embed_texts`, or `retrieve` yields `{"error": "..."}` followed by `{"done": true}` — client never hangs
- [ ] `openai.BadRequestError(code="content_filter")` raised during chunk iteration yields the content-filter error event then `{"done": true}`; tokens already yielded before the error are preserved
- [ ] A chunk with `delta.refusal` set yields an error event containing the refusal text then `{"done": true}`
- [ ] A chunk with `finish_reason == "content_filter"` yields a content-filter error event then `{"done": true}`
- [ ] All three new scenarios have passing tests in `test_chat.py`
- [ ] Existing happy-path and content-filter-at-create tests still pass

## Out of scope

- Frontend error card rendering — the frontend already handles `data.error` events from Phase 5 (`streamChat.js`)
- Retry logic — not in scope for this POC
- Logging infrastructure beyond `logger.error(...)` calls

## Risks

- **`generate()` is a synchronous generator, but `StreamingResponse` runs it in a thread.** A bare `raise` inside `except` after headers are committed would produce a half-written response body. The plan explicitly says "do not re-raise" in the outer envelope — this is why.
- **Test mock for mid-stream `BadRequestError`:** the completion object returned by `.create()` is iterated in a `for` loop. Mocking `side_effect` on the mock's `__iter__` is not straightforward with `MagicMock`; the test should use a custom iterable that raises on the second yield.

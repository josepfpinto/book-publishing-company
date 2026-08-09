---
name: phase-6-sse-hardening
plan: editorial-ai-poc
phase: "phase-6"
type: tasks
---

# SSE Error-Contract Hardening — Tasks

Dependency-ordered. Every task is tagged `[MANUAL]` or `[AGENT]` and states its output.

## Tasks

- [x] **T1** `[AGENT]` Implement SSE error-contract hardening (Gaps A, B, C) in `chat.py` with tests
  - **Output:** `backend/api/routes/chat.py` has a three-layer error envelope; `backend/tests/test_chat.py` has three new passing tests (one per gap); all existing tests still pass
  - **Complexity:** Standard
  - **Depends on:** —
  - **Done when:**
    - `generate()` body is wrapped in `try/except Exception` that yields `{"error": "..."}` + `{"done": true}` on any exception (Gap A)
    - `try/except openai.BadRequestError` covers the `for chunk in completion:` loop, not only `.create()` (Gap B)
    - The chunk loop checks `delta.refusal` and `choice.finish_reason == "content_filter"` and yields appropriate error events (Gap C)
    - Implementation order was A → B → C (inner guards applied inside the outer envelope)
    - `pytest backend/tests/test_chat.py` passes with 3 additional tests: `test_pre_llm_exception_yields_error_and_done`, `test_mid_stream_content_filter_yields_error_and_done`, `test_delta_refusal_yields_error_event`
    - `test_finish_reason_content_filter_yields_error_event` also passes

- [ ] **T2** `[MANUAL]` Verify content-filter error surface in the running UI
  - **Output:** Confirmation that a content-filtered request shows an error card rather than a hung/blank stream
  - **Complexity:** Lightweight
  - **Depends on:** T1, running stack from Story 2 (phase-6-vite-proxy)
  - **Done when:** Sending a message that triggers Azure content policy returns a visible error message in the chat UI within a reasonable timeout; no spinner freeze observed

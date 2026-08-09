"""Tests for api.routes.chat — offline, all external deps mocked."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import openai
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.chat import _SCOPE_LABELS, _sse, router
from core.citation_selection import select_citations as _real_select_citations


# ---------------------------------------------------------------------------
# Content-filter test helper — subclass bypasses httpx.Response requirement
# ---------------------------------------------------------------------------

class _ContentFilterError(openai.BadRequestError):
    """Minimal stand-in for an Azure content_filter BadRequestError."""
    code = "content_filter"

    def __init__(self):
        Exception.__init__(self, "content_filter")


class _MidStreamRaiser:
    """Yields one token chunk then raises _ContentFilterError (simulates mid-stream filter)."""
    def __iter__(self):
        from types import SimpleNamespace as NS
        yield NS(choices=[NS(delta=NS(content="start", refusal=None), finish_reason=None)])
        raise _ContentFilterError()


# ---------------------------------------------------------------------------
# Test app factory
# ---------------------------------------------------------------------------

def _make_app(mock_client, mock_collection=None, deployment="test-deployment"):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.openai_client = mock_client
    app.state.chroma_collection = mock_collection or MagicMock()
    app.state.openai_deployment = deployment
    return app


def _parse_sse(response) -> list[dict]:
    events = []
    for frame in response.text.split("\n\n"):
        frame = frame.strip()
        if frame.startswith("data: "):
            events.append(json.loads(frame[len("data: "):]))
    return events


# ---------------------------------------------------------------------------
# Scope label mapping
# ---------------------------------------------------------------------------

def test_scope_label_little_women():
    assert _SCOPE_LABELS["little_women"] == "Little Women"


def test_scope_label_pride_prejudice():
    assert _SCOPE_LABELS["pride_prejudice"] == "Pride & Prejudice"


def test_scope_label_both():
    assert _SCOPE_LABELS["both"] == "both books"


def test_scope_label_covers_all_expected_book_ids():
    assert set(_SCOPE_LABELS.keys()) == {"little_women", "pride_prejudice", "both"}


# ---------------------------------------------------------------------------
# SSE frame format
# ---------------------------------------------------------------------------

def test_sse_frame_starts_with_data_prefix():
    assert _sse({"token": "hi"}).startswith("data: ")


def test_sse_frame_ends_with_double_newline():
    assert _sse({"done": True}).endswith("\n\n")


def test_sse_frame_contains_valid_json():
    payload = json.loads(_sse({"sources": [{"x": 1}]})[len("data: "):-2])
    assert payload == {"sources": [{"x": 1}]}


# ---------------------------------------------------------------------------
# Content filter error handling
# ---------------------------------------------------------------------------

_COMMON_PATCHES = dict(
    analyze_query=patch("api.routes.chat.analyze_query",
                        return_value=[{"query": "q", "book_id": "little_women"}]),
    embed_texts=patch("api.routes.chat.embed_texts", return_value=[[0.1] * 5]),
    retrieve=patch("api.routes.chat.retrieve", return_value=([], [])),
    build_system_prompt=patch("api.routes.chat.build_system_prompt", return_value="sys"),
    build_messages=patch("api.routes.chat.build_messages", return_value=[]),
)


def test_content_filter_yields_error_event():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = _ContentFilterError()

    with _COMMON_PATCHES["analyze_query"], _COMMON_PATCHES["embed_texts"], \
         _COMMON_PATCHES["retrieve"], _COMMON_PATCHES["build_system_prompt"], \
         _COMMON_PATCHES["build_messages"]:
        with TestClient(_make_app(mock_client)) as client:
            resp = client.post("/api/chat", json={"book_id": "little_women", "message": "test", "history": []})

    events = _parse_sse(resp)
    assert any("error" in e for e in events)
    assert events.count({"done": True}) == 1


def test_content_filter_yields_done_event():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = _ContentFilterError()

    with _COMMON_PATCHES["analyze_query"], _COMMON_PATCHES["embed_texts"], \
         _COMMON_PATCHES["retrieve"], _COMMON_PATCHES["build_system_prompt"], \
         _COMMON_PATCHES["build_messages"]:
        with TestClient(_make_app(mock_client)) as client:
            resp = client.post("/api/chat", json={"book_id": "little_women", "message": "test", "history": []})

    events = _parse_sse(resp)
    assert {"done": True} in events
    assert events.count({"done": True}) == 1


# ---------------------------------------------------------------------------
# Embedding pipeline: one call, correct pairing
# ---------------------------------------------------------------------------

def test_embed_texts_called_once_for_all_sub_queries():
    sub_queries = [
        {"query": "Jo March", "book_id": "little_women"},
        {"query": "Elizabeth Bennet", "book_id": "pride_prejudice"},
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = []

    with patch("api.routes.chat.analyze_query", return_value=sub_queries), \
         patch("api.routes.chat.embed_texts", return_value=[[0.1] * 5, [0.2] * 5]) as mock_embed, \
         patch("api.routes.chat.retrieve", return_value=([], [])), \
         patch("api.routes.chat.build_system_prompt", return_value="sys"), \
         patch("api.routes.chat.build_messages", return_value=[]):

        with TestClient(_make_app(mock_client)) as client:
            client.post("/api/chat", json={"book_id": "both", "message": "compare", "history": []})

        mock_embed.assert_called_once_with(["Jo March", "Elizabeth Bennet"])


def test_embedding_paired_with_correct_book_id():
    sub_queries = [
        {"query": "Jo", "book_id": "little_women"},
        {"query": "Lizzy", "book_id": "pride_prejudice"},
    ]
    captured: list[dict] = []

    def _fake_retrieve(sub_query_inputs, collection, **kwargs):
        captured.extend(sub_query_inputs)
        return [], []

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = []

    with patch("api.routes.chat.analyze_query", return_value=sub_queries), \
         patch("api.routes.chat.embed_texts", return_value=[[1.0, 2.0], [3.0, 4.0]]), \
         patch("api.routes.chat.retrieve", side_effect=_fake_retrieve), \
         patch("api.routes.chat.build_system_prompt", return_value="sys"), \
         patch("api.routes.chat.build_messages", return_value=[]):

        with TestClient(_make_app(mock_client)) as client:
            client.post("/api/chat", json={"book_id": "both", "message": "compare", "history": []})

    assert len(captured) == 2
    assert captured[0] == {"query_embedding": [1.0, 2.0], "book_id": "little_women"}
    assert captured[1] == {"query_embedding": [3.0, 4.0], "book_id": "pride_prejudice"}


# ---------------------------------------------------------------------------
# Sources emitted correctly
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_unknown_book_id_returns_422():
    with TestClient(_make_app(MagicMock())) as client:
        resp = client.post("/api/chat", json={"book_id": "unknown_book", "message": "hi", "history": []})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Token streaming happy path
# ---------------------------------------------------------------------------

def test_token_streaming_yields_token_events():
    from types import SimpleNamespace as NS

    chunk1 = NS(choices=[NS(delta=NS(content="Hello", refusal=None), finish_reason=None)])
    chunk2 = NS(choices=[NS(delta=NS(content=" world", refusal=None), finish_reason=None)])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = [chunk1, chunk2]

    with patch("api.routes.chat.analyze_query", return_value=[{"query": "q", "book_id": "little_women"}]), \
         patch("api.routes.chat.embed_texts", return_value=[[0.1] * 5]), \
         patch("api.routes.chat.retrieve", return_value=([], [])), \
         patch("api.routes.chat.build_system_prompt", return_value="sys"), \
         patch("api.routes.chat.build_messages", return_value=[]):

        with TestClient(_make_app(mock_client)) as client:
            resp = client.post("/api/chat", json={"book_id": "little_women", "message": "hi", "history": []})

    events = _parse_sse(resp)
    token_events = [e for e in events if "token" in e]
    assert token_events == [{"token": "Hello"}, {"token": " world"}]


def test_sources_event_strips_text_field():
    """Sources sent to the frontend must not include the raw chunk text."""
    chunk = {"book_title": "Little Women", "chapter_title": "Ch 1", "chapter_number": 1, "text": "long text"}
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = []

    with patch("api.routes.chat.analyze_query", return_value=[{"query": "q", "book_id": "little_women"}]), \
         patch("api.routes.chat.embed_texts", return_value=[[0.1] * 5]), \
         patch("api.routes.chat.retrieve", return_value=([chunk], [chunk])), \
         patch("api.routes.chat.build_system_prompt", return_value="sys"), \
         patch("api.routes.chat.build_messages", return_value=[]), \
         patch("api.routes.chat.select_citations", return_value=[chunk]):

        with TestClient(_make_app(mock_client)) as client:
            resp = client.post("/api/chat", json={"book_id": "little_women", "message": "q", "history": []})

    events = _parse_sse(resp)
    sources_events = [e for e in events if "sources" in e]
    assert len(sources_events) == 1
    source = sources_events[0]["sources"][0]
    assert "text" not in source
    assert source["book_title"] == "Little Women"


# ---------------------------------------------------------------------------
# Gap A — outer envelope catches pre-LLM exceptions
# ---------------------------------------------------------------------------

def test_pre_llm_exception_yields_error_and_done():
    """Any exception before the LLM call yields error + done; client never hangs."""
    mock_client = MagicMock()

    with patch("api.routes.chat.analyze_query", side_effect=RuntimeError("db down")), \
         _COMMON_PATCHES["embed_texts"], _COMMON_PATCHES["retrieve"], \
         _COMMON_PATCHES["build_system_prompt"], _COMMON_PATCHES["build_messages"]:
        with TestClient(_make_app(mock_client)) as client:
            resp = client.post("/api/chat", json={"book_id": "little_women", "message": "test", "history": []})

    events = _parse_sse(resp)
    assert any("error" in e for e in events)
    assert events.count({"done": True}) == 1


# ---------------------------------------------------------------------------
# Gap B — BadRequestError raised during chunk iteration yields error + done
# ---------------------------------------------------------------------------

def test_mid_stream_content_filter_yields_error_and_done():
    """BadRequestError(content_filter) mid-iteration preserves prior tokens then terminates cleanly."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _MidStreamRaiser()

    with _COMMON_PATCHES["analyze_query"], _COMMON_PATCHES["embed_texts"], \
         _COMMON_PATCHES["retrieve"], _COMMON_PATCHES["build_system_prompt"], \
         _COMMON_PATCHES["build_messages"]:
        with TestClient(_make_app(mock_client)) as client:
            resp = client.post("/api/chat", json={"book_id": "little_women", "message": "test", "history": []})

    events = _parse_sse(resp)
    token_idx = events.index({"token": "start"})
    error_idx = next(i for i, e in enumerate(events) if "error" in e)
    done_idx = events.index({"done": True})
    assert token_idx < error_idx < done_idx
    assert events.count({"done": True}) == 1


# ---------------------------------------------------------------------------
# Gap C — in-stream refusal and content_filter finish_reason
# ---------------------------------------------------------------------------

def test_delta_refusal_yields_error_event():
    """A chunk with delta.refusal set yields an error event containing the refusal text."""
    from types import SimpleNamespace as NS

    refusal_text = "This request is not appropriate."
    chunk = NS(choices=[NS(delta=NS(content=None, refusal=refusal_text), finish_reason=None)])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = [chunk]

    with _COMMON_PATCHES["analyze_query"], _COMMON_PATCHES["embed_texts"], \
         _COMMON_PATCHES["retrieve"], _COMMON_PATCHES["build_system_prompt"], \
         _COMMON_PATCHES["build_messages"]:
        with TestClient(_make_app(mock_client)) as client:
            resp = client.post("/api/chat", json={"book_id": "little_women", "message": "test", "history": []})

    events = _parse_sse(resp)
    error_events = [e for e in events if "error" in e]
    assert len(error_events) == 1
    assert refusal_text in error_events[0]["error"]
    error_idx = next(i for i, e in enumerate(events) if "error" in e)
    done_idx = events.index({"done": True})
    assert error_idx < done_idx
    assert events.count({"done": True}) == 1


def test_finish_reason_content_filter_yields_error_event():
    """A chunk with finish_reason=='content_filter' yields a content-filter error then done."""
    from types import SimpleNamespace as NS

    chunk = NS(choices=[NS(delta=NS(content=None, refusal=None), finish_reason="content_filter")])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = [chunk]

    with _COMMON_PATCHES["analyze_query"], _COMMON_PATCHES["embed_texts"], \
         _COMMON_PATCHES["retrieve"], _COMMON_PATCHES["build_system_prompt"], \
         _COMMON_PATCHES["build_messages"]:
        with TestClient(_make_app(mock_client)) as client:
            resp = client.post("/api/chat", json={"book_id": "little_women", "message": "test", "history": []})

    events = _parse_sse(resp)
    error_events = [e for e in events if "error" in e]
    assert len(error_events) == 1
    assert "Content filtered by Azure policy" in error_events[0]["error"]
    error_idx = next(i for i, e in enumerate(events) if "error" in e)
    done_idx = events.index({"done": True})
    assert error_idx < done_idx
    assert events.count({"done": True}) == 1

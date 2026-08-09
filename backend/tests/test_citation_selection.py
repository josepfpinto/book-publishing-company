"""Tests for core.citation_selection — offline, no live Azure calls."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from core.citation_selection import _validate, select_citations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_client(response_json: dict):
    content = json.dumps(response_json)
    choice = SimpleNamespace(message=SimpleNamespace(content=content))
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[choice])
    return client


def _error_client():
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("API failure")
    return client


_CHUNKS = [
    {"book_title": "Little Women", "chapter_title": "Ch 1", "text": "a"},
    {"book_title": "Little Women", "chapter_title": "Ch 2", "text": "b"},
    {"book_title": "Pride & Prejudice", "chapter_title": "Ch 1", "text": "c"},
    {"book_title": "Little Women", "chapter_title": "Ch 3", "text": "d"},
    {"book_title": "Pride & Prejudice", "chapter_title": "Ch 2", "text": "e"},
]


# ---------------------------------------------------------------------------
# _validate
# ---------------------------------------------------------------------------

def test_validate_returns_valid_indices():
    assert _validate([0, 2], 5) == [0, 2]


def test_validate_clamps_to_max_3():
    assert _validate([0, 1, 2, 3], 5) == [0, 1, 2]


def test_validate_rejects_out_of_range():
    assert _validate([0, 99], 5) == [0]


def test_validate_deduplicates():
    assert _validate([1, 1, 2], 5) == [1, 2]


def test_validate_rejects_non_int():
    assert _validate(["0", 1], 5) == [1]


def test_validate_empty_list_returns_empty():
    assert _validate([], 5) == []


def test_validate_non_list_returns_empty():
    assert _validate({"cited": [0]}, 5) == []


# ---------------------------------------------------------------------------
# select_citations — happy path
# ---------------------------------------------------------------------------

def test_returns_cited_chunks():
    client = _fake_client({"cited": [0, 2]})
    result = select_citations("answer", _CHUNKS, client, "dep")
    assert result == [_CHUNKS[0], _CHUNKS[2]]


def test_model_returns_empty_yields_no_sources():
    client = _fake_client({"cited": []})
    result = select_citations("answer", _CHUNKS, client, "dep")
    assert result == []


def test_caps_at_three():
    client = _fake_client({"cited": [0, 1, 2, 3, 4]})
    result = select_citations("answer", _CHUNKS, client, "dep")
    assert len(result) == 3


def test_empty_context_short_circuits_without_api_call():
    client = MagicMock()
    result = select_citations("answer", [], client, "dep")
    assert result == []
    client.chat.completions.create.assert_not_called()


# ---------------------------------------------------------------------------
# select_citations — fallback paths
# ---------------------------------------------------------------------------

def test_api_error_returns_top_chunk():
    result = select_citations("answer", _CHUNKS, _error_client(), "dep")
    assert result == [_CHUNKS[0]]


def test_invalid_json_returns_top_chunk():
    client = MagicMock()
    bad = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="not json{"))])
    client.chat.completions.create.return_value = bad
    result = select_citations("answer", _CHUNKS, client, "dep")
    assert result == [_CHUNKS[0]]


def test_missing_cited_field_returns_empty():
    client = _fake_client({"other_field": [0]})
    result = select_citations("answer", _CHUNKS, client, "dep")
    assert result == []

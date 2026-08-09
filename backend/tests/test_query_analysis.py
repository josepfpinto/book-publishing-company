"""Tests for core.query_analysis — offline, no live Azure calls."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.query_analysis import analyze_query, _scope_aware_fallback, _validate_and_repair


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_client(response_json: dict):
    """Return a minimal fake openai_client whose completions.create returns response_json."""
    content = json.dumps(response_json)
    choice = SimpleNamespace(message=SimpleNamespace(content=content))
    completion = SimpleNamespace(choices=[choice])
    client = MagicMock()
    client.chat.completions.create.return_value = completion
    return client


def _error_client():
    """Return a fake client that raises on every call."""
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("simulated API failure")
    return client


# ---------------------------------------------------------------------------
# _scope_aware_fallback
# ---------------------------------------------------------------------------

def test_fallback_both_returns_two_distinct_books():
    result = _scope_aware_fallback("Compare the heroines", "both")
    assert len(result) == 2
    book_ids = {sq["book_id"] for sq in result}
    assert book_ids == {"little_women", "pride_prejudice"}


def test_fallback_single_book_returns_one():
    result = _scope_aware_fallback("What is Jo like?", "little_women")
    assert result == [{"query": "What is Jo like?", "book_id": "little_women"}]


# ---------------------------------------------------------------------------
# _validate_and_repair
# ---------------------------------------------------------------------------

def test_validate_passes_valid_both_result():
    raw = [
        {"query": "Jo in LW", "book_id": "little_women"},
        {"query": "Lizzy in PP", "book_id": "pride_prejudice"},
    ]
    result = _validate_and_repair(raw, "Compare heroines", "both")
    assert len(result) == 2
    assert {sq["book_id"] for sq in result} == {"little_women", "pride_prejudice"}


def test_validate_repairs_both_missing_one_book():
    raw = [{"query": "Lizzy in PP", "book_id": "pride_prejudice"}]
    result = _validate_and_repair(raw, "Compare heroines", "both")
    assert len(result) == 2
    assert {sq["book_id"] for sq in result} == {"little_women", "pride_prejudice"}


def test_validate_repairs_both_with_wrong_book_ids():
    raw = [
        {"query": "Jo", "book_id": "little_women"},
        {"query": "Lizzy", "book_id": "little_women"},  # wrong: both same
    ]
    result = _validate_and_repair(raw, "Compare heroines", "both")
    assert {sq["book_id"] for sq in result} == {"little_women", "pride_prejudice"}


def test_validate_returns_fallback_on_empty():
    result = _validate_and_repair([], "What is Jo like?", "little_women")
    assert result == [{"query": "What is Jo like?", "book_id": "little_women"}]


def test_validate_returns_fallback_on_invalid_items():
    result = _validate_and_repair([{"not_a_query": "x"}], "msg", "little_women")
    assert len(result) == 1
    assert result[0]["book_id"] == "little_women"


def test_validate_caps_both_at_exactly_two_when_llm_over_produces():
    # LLM returns 3 valid items: 2×little_women + 1×pride_prejudice
    raw = [
        {"query": "LW query 1", "book_id": "little_women"},
        {"query": "LW query 2", "book_id": "little_women"},
        {"query": "PP query", "book_id": "pride_prejudice"},
    ]
    result = _validate_and_repair(raw, "Compare heroines", "both")
    assert len(result) == 2
    assert {sq["book_id"] for sq in result} == {"little_women", "pride_prejudice"}
    # First matching query per book should win
    assert result[0]["query"] == "LW query 1"
    assert result[1]["query"] == "PP query"


def test_validate_caps_single_book_at_two():
    raw = [
        {"query": "q1", "book_id": "little_women"},
        {"query": "q2", "book_id": "little_women"},
        {"query": "q3", "book_id": "little_women"},
    ]
    result = _validate_and_repair(raw, "long compound question", "little_women")
    assert len(result) == 2


# ---------------------------------------------------------------------------
# analyze_query — via fake LLM client
# ---------------------------------------------------------------------------

def test_both_returns_two_distinct_book_ids():
    client = _fake_client({"sub_queries": [
        {"query": "Jo March", "book_id": "little_women"},
        {"query": "Elizabeth Bennet", "book_id": "pride_prejudice"},
    ]})
    result = analyze_query("Compare the heroines", "both", client)
    assert len(result) == 2
    assert {sq["book_id"] for sq in result} == {"little_women", "pride_prejudice"}


def test_single_book_simple_question_returns_one():
    client = _fake_client({"sub_queries": [
        {"query": "What is Jo March like?", "book_id": "little_women"},
    ]})
    result = analyze_query("What is Jo like?", "little_women", client)
    assert len(result) == 1
    assert result[0]["book_id"] == "little_women"


def test_compound_single_book_question_returns_two_same_book():
    client = _fake_client({"sub_queries": [
        {"query": "What happens in chapter 1?", "book_id": "little_women"},
        {"query": "What happens at the end of the book?", "book_id": "little_women"},
    ]})
    result = analyze_query(
        "What happens in chapter 1 and what happens at the end?", "little_women", client
    )
    assert len(result) == 2
    assert all(sq["book_id"] == "little_women" for sq in result)


def test_api_error_returns_single_fallback_for_single_book():
    result = analyze_query("What is Jo like?", "little_women", _error_client())
    assert result == [{"query": "What is Jo like?", "book_id": "little_women"}]


def test_api_error_returns_two_fallbacks_for_both():
    result = analyze_query("Compare heroines", "both", _error_client())
    assert len(result) == 2
    assert {sq["book_id"] for sq in result} == {"little_women", "pride_prejudice"}


def test_json_parse_failure_falls_back():
    client = MagicMock()
    bad_choice = SimpleNamespace(message=SimpleNamespace(content="not valid json {"))
    client.chat.completions.create.return_value = SimpleNamespace(choices=[bad_choice])
    result = analyze_query("What is Jo like?", "little_women", client)
    assert result == [{"query": "What is Jo like?", "book_id": "little_women"}]

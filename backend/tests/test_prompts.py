"""Tests for core.prompts — pure-function, no I/O."""
from __future__ import annotations

import pytest

from core.prompts import build_messages, build_system_prompt


# ---------------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------------

def test_system_prompt_contains_scope_label():
    prompt = build_system_prompt("Little Women")
    assert "Little Women" in prompt


def test_system_prompt_instructs_citation():
    prompt = build_system_prompt("both books")
    assert "cite" in prompt.lower() or "citation" in prompt.lower() or "book" in prompt.lower()


def test_system_prompt_instructs_passages_only():
    prompt = build_system_prompt("Pride & Prejudice")
    lower = prompt.lower()
    assert "only" in lower or "retrieved" in lower or "provided" in lower


# ---------------------------------------------------------------------------
# build_messages — structure
# ---------------------------------------------------------------------------

def _history(n_prior: int = 2):
    turns = []
    for i in range(n_prior):
        turns.append({"role": "user", "content": f"prior question {i}"})
        turns.append({"role": "assistant", "content": f"prior answer {i}"})
    turns.append({"role": "user", "content": "current question"})
    return turns


def _chunks(n: int = 2):
    return [
        {"text": f"passage {i}", "book_title": "Little Women", "chapter_title": f"Chapter {i + 1}"}
        for i in range(n)
    ]


def test_first_message_is_system_prompt():
    history = _history()
    system_prompt = build_system_prompt("Little Women")
    messages = build_messages(system_prompt, history, _chunks(), "Little Women")
    assert messages[0] == {"role": "system", "content": system_prompt}


def test_prior_turns_tagged_with_scope():
    history = _history(n_prior=2)
    messages = build_messages(build_system_prompt("Little Women"), history, [], "Little Women")
    # prior turns are all but the last
    prior_messages = messages[1:-1]  # skip system, skip current question
    for msg in prior_messages:
        assert "[asked under: Little Women]" in msg["content"]


def test_current_question_unmodified():
    history = _history(n_prior=1)
    current = history[-1]
    messages = build_messages(build_system_prompt("Little Women"), history, [], "Little Women")
    # current question should appear in messages as-is
    current_in_messages = [m for m in messages if m.get("content") == current["content"]]
    assert len(current_in_messages) >= 1


def test_context_chunks_formatted_correctly():
    chunks = [
        {"text": "Jo was brave.", "book_title": "Little Women", "chapter_title": "Playing Pilgrims"},
    ]
    messages = build_messages(build_system_prompt("Little Women"), _history(0), chunks, "Little Women")
    context_msg = messages[-1]
    assert "[CHUNK 1]" in context_msg["content"]
    assert "Little Women" in context_msg["content"]
    assert "Playing Pilgrims" in context_msg["content"]
    assert "Jo was brave." in context_msg["content"]


def test_multiple_chunks_all_indexed():
    chunks = _chunks(3)
    messages = build_messages(build_system_prompt("both books"), _history(0), chunks, "both books")
    context_msg = messages[-1]
    assert "[CHUNK 1]" in context_msg["content"]
    assert "[CHUNK 2]" in context_msg["content"]
    assert "[CHUNK 3]" in context_msg["content"]


def test_empty_history_only_returns_system_and_context():
    chunks = _chunks(1)
    messages = build_messages(build_system_prompt("Little Women"), [], chunks, "Little Women")
    assert messages[0]["role"] == "system"
    assert any("[CHUNK 1]" in m.get("content", "") for m in messages)


def test_no_chunks_produces_no_context_message():
    history = _history(1)
    messages = build_messages(build_system_prompt("Little Women"), history, [], "Little Women")
    for m in messages:
        assert "[CHUNK" not in m.get("content", "")


def test_no_scope_label_produces_no_tag():
    history = _history(n_prior=1)
    messages = build_messages(build_system_prompt(""), history, [], scope_label="")
    prior_messages = [m for m in messages if m["role"] != "system"]
    for msg in prior_messages[:-1]:
        assert "[asked under:" not in msg.get("content", "")

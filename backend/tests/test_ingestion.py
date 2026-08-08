"""Ingestion verification gate — six offline assertions against parser + citation output."""
from __future__ import annotations

import os
import re

import pytest

from core.citations import populate_excerpts
from core.ingestion import ingest_book

_BOOKS_DIR = os.getenv("BOOKS_DIR", "books")

_BOOK_DEFS = [
    ("little_women", "Little Women", "little_women.html"),
    ("pride_prejudice", "Pride and Prejudice", "pride_prejudice.html"),
]


@pytest.fixture(scope="module")
def all_chunks():
    chunks = []
    for book_id, book_title, fname in _BOOK_DEFS:
        path = os.path.join(_BOOKS_DIR, fname)
        c = ingest_book(path, book_id, book_title)
        populate_excerpts(c)
        chunks.extend(c)
    return chunks


def _label(c: dict) -> str:
    return f"{c['book_id']} ch{c['chapter_number']} chunk{c['chunk_index']}"


def test_chapter_count_lw(all_chunks):
    chapters = {c["chapter_number"] for c in all_chunks if c["book_id"] == "little_women"}
    assert chapters == set(range(1, 48)), f"Expected chapters 1-47, got {sorted(chapters)}"


def test_chapter_count_pp(all_chunks):
    chapters = {c["chapter_number"] for c in all_chunks if c["book_id"] == "pride_prejudice"}
    assert chapters == set(range(1, 62)), f"Expected chapters 1-61, got {sorted(chapters)}"


def test_no_page_number_leakage(all_chunks):
    pattern = re.compile(r"\{[\divxlcIVXLC]+\}")
    for c in all_chunks:
        assert not pattern.search(c["text"]), f"Page number leakage in {_label(c)}"


def test_no_back_matter_leakage(all_chunks):
    markers = [
        "The Works of Louisa May Alcott",
        "Transcriber's Note",
        "Project Gutenberg",
        "START OF THE PROJECT",
    ]
    for c in all_chunks:
        for m in markers:
            assert m not in c["text"], f"Back matter leakage '{m}' in {_label(c)}"


def test_chapter_first_chunk_open(all_chunks):
    open_quotes = '"\'“‘'  # ASCII and curly open-quote variants
    for c in all_chunks:
        if c["chunk_index"] == 0:
            first = c["text"][:1]
            assert first.isupper() or first in open_quotes, (
                f"{_label(c)} opens with {repr(first)}"
            )


def test_metadata_schema(all_chunks):
    # terminal punctuation from citations.py splitter + ellipsis suffix
    terminal = re.compile(r'[.!?""…”]$')
    for c in all_chunks:
        label = _label(c)
        assert isinstance(c.get("book_title"), str), f"Missing book_title in {label}"
        assert isinstance(c.get("chapter_number"), int), f"Missing chapter_number in {label}"
        assert isinstance(c.get("excerpt"), str) and c["excerpt"], f"Missing/empty excerpt in {label}"
        assert terminal.search(c["excerpt"]), f"excerpt ends mid-word in {label}: {repr(c['excerpt'][-10:])}"
        assert all(v is not None for v in c.values()), f"None value in {label}"

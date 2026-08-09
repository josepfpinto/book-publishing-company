"""Tests for core.retrieval — offline, uses a fake ChromaDB collection."""
from __future__ import annotations

import pytest

from core.retrieval import retrieve


# ---------------------------------------------------------------------------
# Fake collection
# ---------------------------------------------------------------------------

class FakeCollection:
    """Records query calls and returns configurable results."""

    def __init__(self, pages: dict[str, dict]):
        """
        pages: mapping of book_id -> ChromaDB-shaped response dict
               (ids, documents, metadatas, distances all as nested lists)
        """
        self._pages = pages
        self.calls: list[dict] = []

    def query(self, *, query_embeddings, n_results, where, include):
        self.calls.append({"where": where, "n_results": n_results})
        book_id = where["book_id"]
        return self._pages.get(book_id, {
            "ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]
        })


def _make_pages(book_id: str, n: int, base_dist: float = 0.1) -> dict:
    """Return a fake page dict with n chunks for book_id."""
    ids = [f"{book_id}_chunk_{i}" for i in range(n)]
    docs = [f"text of {book_id} chunk {i}" for i in range(n)]
    metas = [{"book_id": book_id, "book_title": book_id.replace("_", " ").title(),
               "chapter_title": f"Chapter {i + 1}", "chapter_number": i + 1}
             for i in range(n)]
    dists = [base_dist + i * 0.05 for i in range(n)]
    return {"ids": [ids], "documents": [docs], "metadatas": [metas], "distances": [dists]}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_one_sub_query_triggers_one_collection_call():
    pages = {"little_women": _make_pages("little_women", 5)}
    col = FakeCollection(pages)
    sub_queries = [{"query_embedding": [0.1] * 10, "book_id": "little_women"}]
    retrieve(sub_queries, col)
    assert len(col.calls) == 1
    assert col.calls[0]["where"] == {"book_id": "little_women"}


def test_two_sub_queries_trigger_two_collection_calls_each_with_correct_filter():
    pages = {
        "little_women": _make_pages("little_women", 5),
        "pride_prejudice": _make_pages("pride_prejudice", 5),
    }
    col = FakeCollection(pages)
    sub_queries = [
        {"query_embedding": [0.1] * 10, "book_id": "little_women"},
        {"query_embedding": [0.2] * 10, "book_id": "pride_prejudice"},
    ]
    retrieve(sub_queries, col)
    assert len(col.calls) == 2
    book_ids = {c["where"]["book_id"] for c in col.calls}
    assert book_ids == {"little_women", "pride_prejudice"}


def test_duplicate_chunk_id_kept_at_highest_score():
    shared_id = "shared_chunk"
    # same chunk appears in both sub-query results with different distances
    page_a = {
        "ids": [[shared_id, "unique_a"]],
        "documents": [["shared doc", "unique a doc"]],
        "metadatas": [[
            {"book_id": "little_women", "book_title": "Little Women", "chapter_title": "Ch 1", "chapter_number": 1},
            {"book_id": "little_women", "book_title": "Little Women", "chapter_title": "Ch 2", "chapter_number": 2},
        ]],
        "distances": [[0.1, 0.3]],  # shared score = 0.9
    }
    page_b = {
        "ids": [[shared_id, "unique_b"]],
        "documents": [["shared doc", "unique b doc"]],
        "metadatas": [[
            {"book_id": "pride_prejudice", "book_title": "P&P", "chapter_title": "Ch 1", "chapter_number": 1},
            {"book_id": "pride_prejudice", "book_title": "P&P", "chapter_title": "Ch 2", "chapter_number": 2},
        ]],
        "distances": [[0.5, 0.2]],  # shared score = 0.5 (lower — should be discarded)
    }
    col = FakeCollection({"little_women": page_a, "pride_prejudice": page_b})
    sub_queries = [
        {"query_embedding": [0.1] * 10, "book_id": "little_women"},
        {"query_embedding": [0.2] * 10, "book_id": "pride_prejudice"},
    ]
    context, citable = retrieve(sub_queries, col)
    # shared_id should appear exactly once
    shared_hits = [c for c in context if c.get("book_title") == "Little Women" and "shared" in c["text"]]
    assert len(shared_hits) == 1


def test_context_chunks_capped_at_5_citable_at_3():
    pages = {"little_women": _make_pages("little_women", 10)}
    col = FakeCollection(pages)
    sub_queries = [{"query_embedding": [0.1] * 10, "book_id": "little_women"}]
    context, citable = retrieve(sub_queries, col, n_results=10)
    assert len(context) <= 5
    assert len(citable) <= 3


def test_no_none_values_in_returned_metadata():
    page = {
        "ids": [["chunk_1"]],
        "documents": [["some text"]],
        "metadatas": [[{"book_id": "little_women", "page_start": None, "chapter_title": "Ch 1", "chapter_number": 1}]],
        "distances": [[0.1]],
    }
    col = FakeCollection({"little_women": page})
    sub_queries = [{"query_embedding": [0.1] * 10, "book_id": "little_women"}]
    context, _ = retrieve(sub_queries, col)
    for chunk in context:
        for v in chunk.values():
            assert v is not None, f"Found None value in chunk: {chunk}"


def test_results_sorted_by_score_descending():
    pages = {"little_women": _make_pages("little_women", 5, base_dist=0.05)}
    col = FakeCollection(pages)
    sub_queries = [{"query_embedding": [0.1] * 10, "book_id": "little_women"}]
    context, _ = retrieve(sub_queries, col)
    # lower distance → higher score → should appear first
    assert context[0]["chapter_number"] < context[-1]["chapter_number"]


def test_both_sub_query_results_merged_when_no_duplicates():
    """All unique chunks from both sub-queries should appear in context."""
    lw_page = _make_pages("little_women", 3, base_dist=0.1)
    pp_page = _make_pages("pride_prejudice", 3, base_dist=0.2)
    col = FakeCollection({"little_women": lw_page, "pride_prejudice": pp_page})
    sub_queries = [
        {"query_embedding": [0.1] * 10, "book_id": "little_women"},
        {"query_embedding": [0.2] * 10, "book_id": "pride_prejudice"},
    ]
    context, _ = retrieve(sub_queries, col)
    # 3 LW + 3 PP = 6 unique chunks, but context capped at 5
    assert len(context) == 5
    books_in_context = {c["book_id"] for c in context}
    assert "little_women" in books_in_context
    assert "pride_prejudice" in books_in_context


def test_none_document_becomes_empty_string_not_none():
    page = {
        "ids": [["chunk_null_doc"]],
        "documents": [[None]],
        "metadatas": [[{"book_id": "little_women", "chapter_title": "Ch 1", "chapter_number": 1}]],
        "distances": [[0.1]],
    }
    col = FakeCollection({"little_women": page})
    sub_queries = [{"query_embedding": [0.1] * 10, "book_id": "little_women"}]
    context, _ = retrieve(sub_queries, col)
    assert len(context) == 1
    assert context[0]["text"] is not None
    assert context[0]["text"] == ""

"""Tests for api.routes.books — offline, uses a fake ChromaDB collection."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.books import router


class _FakeCollection:
    def __init__(self, metadatas: list[dict]):
        self._metadatas = metadatas

    def get(self, *, include):
        return {"metadatas": self._metadatas}


def _make_client(metadatas: list[dict]) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.chroma_collection = _FakeCollection(metadatas)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Aggregation correctness
# ---------------------------------------------------------------------------

def test_returns_one_entry_per_book():
    metas = [
        {"book_id": "little_women", "book_title": "Little Women", "chapter_number": 1},
        {"book_id": "little_women", "book_title": "Little Women", "chapter_number": 2},
        {"book_id": "pride_prejudice", "book_title": "Pride and Prejudice", "chapter_number": 1},
    ]
    client = _make_client(metas)
    resp = client.get("/api/books")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_chapter_count_is_distinct_chapter_numbers():
    metas = [
        {"book_id": "little_women", "book_title": "Little Women", "chapter_number": 1},
        {"book_id": "little_women", "book_title": "Little Women", "chapter_number": 1},
        {"book_id": "little_women", "book_title": "Little Women", "chapter_number": 2},
    ]
    client = _make_client(metas)
    resp = client.get("/api/books")
    book = resp.json()[0]
    assert book["chapter_count"] == 2


def test_response_contains_id_title_chapter_count():
    metas = [
        {"book_id": "little_women", "book_title": "Little Women", "chapter_number": 1},
    ]
    client = _make_client(metas)
    book = client.get("/api/books").json()[0]
    assert "id" in book
    assert "title" in book
    assert "chapter_count" in book


def test_id_matches_book_id_metadata():
    metas = [{"book_id": "pride_prejudice", "book_title": "Pride and Prejudice", "chapter_number": 1}]
    client = _make_client(metas)
    book = client.get("/api/books").json()[0]
    assert book["id"] == "pride_prejudice"


def test_title_matches_book_title_metadata():
    metas = [{"book_id": "little_women", "book_title": "Little Women", "chapter_number": 1}]
    client = _make_client(metas)
    book = client.get("/api/books").json()[0]
    assert book["title"] == "Little Women"


def test_chunk_without_book_id_is_skipped():
    metas = [
        {"book_title": "Unknown", "chapter_number": 1},  # no book_id
        {"book_id": "little_women", "book_title": "Little Women", "chapter_number": 1},
    ]
    client = _make_client(metas)
    resp = client.get("/api/books")
    assert len(resp.json()) == 1


def test_chunk_without_chapter_number_does_not_crash():
    metas = [
        {"book_id": "little_women", "book_title": "Little Women"},  # no chapter_number
        {"book_id": "little_women", "book_title": "Little Women", "chapter_number": 1},
    ]
    client = _make_client(metas)
    resp = client.get("/api/books")
    assert resp.status_code == 200
    assert resp.json()[0]["chapter_count"] == 1


def test_empty_collection_returns_empty_list():
    client = _make_client([])
    assert client.get("/api/books").json() == []

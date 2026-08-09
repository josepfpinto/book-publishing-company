"""GET /api/books — sanity endpoint listing ingested books."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/books")
def get_books(request: Request) -> list[dict]:
    collection = request.app.state.chroma_collection
    results = collection.get(include=["metadatas"])
    books: dict[str, dict] = {}
    for meta in results["metadatas"]:
        book_id = meta.get("book_id")
        if book_id is None:
            continue
        if book_id not in books:
            books[book_id] = {
                "id": book_id,
                "title": meta.get("book_title", book_id),
                "chapters": set(),
            }
        chapter = meta.get("chapter_number")
        if chapter is not None:
            books[book_id]["chapters"].add(chapter)
    return [
        {"id": v["id"], "title": v["title"], "chapter_count": len(v["chapters"])}
        for v in books.values()
    ]

"""One-shot ingestion CLI: parse both books, embed chunks, write to ChromaDB."""
from __future__ import annotations

import os
import sys

import chromadb
from dotenv import load_dotenv

load_dotenv()

from core.citations import populate_excerpts
from core.embeddings import embed_texts
from core.ingestion import ingest_book

BOOKS_DIR = os.getenv("BOOKS_DIR", "books")
BOOKS = [
    {"path": f"{BOOKS_DIR}/little_women.html", "book_id": "little_women", "book_title": "Little Women"},
    {"path": f"{BOOKS_DIR}/pride_prejudice.html", "book_id": "pride_prejudice", "book_title": "Pride and Prejudice"},
]


def main() -> None:
    client = chromadb.PersistentClient(path="./data/chroma")
    collection = client.get_or_create_collection("books")

    for book in BOOKS:
        print(f"Parsing {book['book_title']}...", file=sys.stderr)
        chunks = ingest_book(book["path"], book["book_id"], book["book_title"])
        populate_excerpts(chunks)

        texts = [c["text"] for c in chunks]
        ids = [
            f"{c['book_id']}_ch{c['chapter_number']:03d}_chunk{c['chunk_index']:03d}"
            for c in chunks
        ]
        metadatas = []
        for i, chunk in enumerate(chunks):
            meta = {k: v for k, v in chunk.items() if k != "text"}
            if meta.get("excerpt") == "":
                print(f"Warning: empty excerpt for {ids[i]}", file=sys.stderr)
                del meta["excerpt"]
            metadatas.append(meta)

        embeddings = embed_texts(texts)
        collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        print(f"{book['book_title']}: {len(chunks)} chunks ingested")


if __name__ == "__main__":
    main()

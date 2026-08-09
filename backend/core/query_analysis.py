"""Always-on query decomposition — every request becomes 1 or 2 sub-queries."""
from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_BOOKS = {"little_women", "pride_prejudice"}

_SYSTEM_PROMPT = """\
You are a retrieval query planner for a literary chat assistant.
Split the user's question into targeted sub-queries for semantic search.

Rules:
- book_id "both": return EXACTLY 2 sub-queries, one with book_id "little_women"
  and one with book_id "pride_prejudice", each rewritten to focus on that book.
- book_id is a single book: return 1 sub-query (refined restatement) unless the
  question clearly contains 2 separable parts — then return 2, both with the same book_id.

Respond with valid JSON only (no markdown):
{"sub_queries": [{"query": "...", "book_id": "..."}, ...]}
"""


def _scope_aware_fallback(message: str, book_id: str) -> list[dict]:
    """Return the fallback sub-queries without calling the LLM."""
    if book_id == "both":
        return [
            {"query": message, "book_id": "little_women"},
            {"query": message, "book_id": "pride_prejudice"},
        ]
    return [{"query": message, "book_id": book_id}]


def _validate_and_repair(sub_queries: list[dict], message: str, book_id: str) -> list[dict]:
    """Ensure sub_queries match the spec; repair silently rather than crashing."""
    if not isinstance(sub_queries, list) or not sub_queries:
        return _scope_aware_fallback(message, book_id)

    valid = []
    for sq in sub_queries:
        if isinstance(sq, dict) and isinstance(sq.get("query"), str) and isinstance(sq.get("book_id"), str):
            valid.append(sq)

    if not valid:
        return _scope_aware_fallback(message, book_id)

    if book_id == "both":
        # Need exactly one sub-query per book, keyed in order.
        by_book: dict[str, str] = {}
        for sq in valid:
            if sq["book_id"] in _BOOKS and sq["book_id"] not in by_book:
                by_book[sq["book_id"]] = sq["query"]
        if set(by_book) != _BOOKS:
            # LLM didn't produce one per book — rebuild from the first query found
            first_query = valid[0]["query"]
            by_book = {
                "little_women": first_query,
                "pride_prejudice": first_query,
            }
        return [
            {"query": by_book["little_women"], "book_id": "little_women"},
            {"query": by_book["pride_prejudice"], "book_id": "pride_prejudice"},
        ]

    # Single-book: spec allows 1 or 2, never more
    return valid[:2]


def analyze_query(message: str, book_id: str, openai_client) -> list[dict]:
    """Decompose message into 1-2 sub-queries with book targets.

    Returns 1 or 2 dicts, each {"query": str, "book_id": str}.
    book_id "both" always yields exactly 2 items with distinct book_ids.
    Falls back to a scope-aware default on any API or parse failure.
    """
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    try:
        response = openai_client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"book_id: {book_id}\nquestion: {message}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content)
        raw = data.get("sub_queries", [])
        return _validate_and_repair(raw, message, book_id)
    except Exception:
        logger.exception("analyze_query failed, using scope-aware fallback")
        return _scope_aware_fallback(message, book_id)

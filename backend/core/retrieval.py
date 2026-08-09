"""Multi-sub-query retrieval with cross-sub-query deduplication and score merge."""
from __future__ import annotations


def retrieve(
    sub_queries: list[dict],
    collection,
    n_results: int = 5,
) -> tuple[list[dict], list[dict]]:
    """Retrieve chunks for each sub-query and merge into a single ranked list.

    Each sub_query must contain:
        "query_embedding": list[float]  — pre-computed by the calling route
        "book_id": str                  — used as the ChromaDB where-filter

    Returns (context_chunks, citable) where:
        context_chunks = top-5 after dedup + sort
        citable        = top-3 from context_chunks (for citation display)
    Each dict contains the chunk text plus its raw ChromaDB metadata (no None values).
    """
    # chunk_id -> (score, chunk_dict) — keeps highest score across sub-queries
    best: dict[str, tuple[float, dict]] = {}

    for sq in sub_queries:
        results = collection.query(
            query_embeddings=[sq["query_embedding"]],
            n_results=n_results,
            where={"book_id": sq["book_id"]},
            include=["documents", "metadatas", "distances"],
        )

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
            score = 1.0 - dist
            clean_meta = {k: v for k, v in meta.items() if v is not None}
            chunk = {"text": doc if doc is not None else "", **clean_meta}
            if chunk_id not in best or score > best[chunk_id][0]:
                best[chunk_id] = (score, chunk)

    ranked = [chunk for _, chunk in sorted(best.values(), key=lambda t: t[0], reverse=True)]
    return ranked[:5], ranked[:3]

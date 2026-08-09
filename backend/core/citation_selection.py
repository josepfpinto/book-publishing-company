"""Post-stream citation selection — asks the model which chunks it actually used."""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def _validate(cited: object, n_chunks: int) -> list[int]:
    """Return a deduplicated, range-clamped list of valid indices (max 3)."""
    if not isinstance(cited, list):
        return []
    seen: set[int] = set()
    valid: list[int] = []
    for i in cited:
        if isinstance(i, int) and 0 <= i < n_chunks and i not in seen:
            seen.add(i)
            valid.append(i)
        if len(valid) == 3:
            break
    return valid


def select_citations(
    full_answer: str,
    context_chunks: list[dict],
    openai_client,
    deployment: str,
) -> list[dict]:
    """Return 0–3 chunks the model actually drew from.

    Sends one json_object call after streaming completes.
    Returns [] when the model explicitly indicates no chunk was used.
    Falls back to the top chunk on any API or parse failure.
    """
    if not context_chunks:
        return []

    numbered = "\n".join(
        f"[{i}] {c.get('book_title', '')} — {c.get('chapter_title', '')}"
        for i, c in enumerate(context_chunks)
    )
    try:
        resp = openai_client.chat.completions.create(
            model=deployment,
            messages=[{
                "role": "user",
                "content": (
                    f"Answer:\n{full_answer}\n\n"
                    f"Available chunks:\n{numbered}\n\n"
                    "Which chunk indices (0-based) did the answer draw from? "
                    'Respond with valid JSON only, no markdown: {"cited": [0, 2]}\n'
                    "Use [] if no chunk was relevant. Maximum 3 indices."
                ),
            }],
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        indices = _validate(data.get("cited", []), len(context_chunks))
        return [context_chunks[i] for i in indices]
    except Exception:
        logger.exception("select_citations failed, using fallback")
        return context_chunks[:1]

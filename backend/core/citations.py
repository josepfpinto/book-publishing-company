"""Citation composition layer: excerpt builder and chapter heading composer.

Implements plan §4 (Citation schema, Excerpt rule). Originally translated from
the excerpt() and cite() functions of the Phase 3 parser probe, which has since
been deleted — plan §4 is now the authoritative specification.

Behaviour is pinned by tests/test_citations.py (unit) and tests/test_ingestion.py
(integration, against real parsed chapters).
"""
from __future__ import annotations

import re

# sentence boundary: split after . ! ? ” (right curly quote) " (straight quote)
# U+201D + U+0022 are both required — the transcriptions mix them.
_SENT = re.compile(r'(?<=[.!?”"])\s+')


def build_excerpt(text: str, minimum: int = 80) -> str:
    """Extract >= 1 complete sentence from text.

    Accumulates whole sentences until len(out) >= minimum, then stops.
    Appends '…' only if the excerpt is shorter than the full text.
    Never cuts mid-word — splits only on sentence boundaries.

    The excerpt has no upper bound: a single sentence longer than `minimum`
    is emitted whole rather than truncated, since cutting it would break the
    "at least one complete sentence" contract (plan §4 Excerpt rule).
    """
    out = ""
    for s in _SENT.split(text):
        out = (out + " " + s).strip()
        if len(out) >= minimum:
            break
    return out + ("…" if len(out) < len(text.strip()) else "")


def compose_heading(
    chapter_number: int,
    chapter_title: str,
    page_start: str | None,
    page_end: str | None,
) -> str:
    """Compose the SourceCard chapter line with graceful degradation.

    Rules (plan §4 Citation schema):
      Base:    'Chapter {n}'
      +title:  ' — {chapter_title}'  only when chapter_title != f'Chapter {n}'
      +page:   ' · p. {page_start}' when page_start present, same as page_end (or absent)
      +pages:  ' · pp. {page_start}–{page_end}' when both present and differ
    """
    head = f"Chapter {chapter_number}"
    if chapter_title != f"Chapter {chapter_number}":
        head += f" — {chapter_title}"  # em dash
    if page_start:
        if page_end and page_end != page_start:
            head += f" · pp. {page_start}–{page_end}"  # middle dot, en dash
        else:
            head += f" · p. {page_start}"
    return head


def populate_excerpts(chunks: list[dict]) -> list[dict]:
    """Overwrite the 'excerpt' key in each chunk dict in-place. Returns the same list."""
    for chunk in chunks:
        chunk["excerpt"] = build_excerpt(chunk["text"])
    return chunks

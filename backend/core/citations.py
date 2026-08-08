"""Citation composition layer: excerpt builder and chapter heading composer.

Translated directly from the excerpt() and cite() functions in
docs/tasks/editorial-ai-poc.parser-probe.py, per plan §4 (Citation schema,
Excerpt rule).
"""
from __future__ import annotations

import re

# sentence boundary: split after . ! ? ” (right curly quote) " (straight quote)
# matches the probe's validated regex exactly: r'(?<=[.!?""])\s+'
_SENT = re.compile(r'(?<=[.!?”"])\s+')


def build_excerpt(text: str, target: int = 230, minimum: int = 80) -> str:
    """Extract >= 1 complete sentence from text.

    Accumulates sentences until len(out) >= minimum, stops before target.
    Appends '...' only if excerpt is shorter than the full text.
    Never cuts mid-word — splits only on sentence boundaries.
    """
    sents = _SENT.split(text)
    out = ""
    for s in sents:
        if out and len(out) + len(s) + 1 > target:
            break
        out = (out + " " + s).strip()
        if len(out) >= minimum:
            break
    if not out:
        # fallback: at least one word-boundary-safe fragment
        out = text[:target].rsplit(" ", 1)[0]
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


if __name__ == "__main__":
    # Canonical heading assertions from tasks.md and plan §4
    cases = [
        (
            compose_heading(9, "Meg Goes to Vanity Fair", None, None),
            "Chapter 9 — Meg Goes to Vanity Fair",
        ),
        (
            compose_heading(26, "Chapter 26", "182", "183"),
            "Chapter 26 · pp. 182–183",
        ),
        (
            compose_heading(26, "Chapter 26", "182", None),
            "Chapter 26 · p. 182",
        ),
        (
            compose_heading(26, "Chapter 26", None, None),
            "Chapter 26",
        ),
    ]
    all_pass = True
    for result, expected in cases:
        ok = result == expected
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {repr(result)}")
        if not ok:
            print(f"        expected: {repr(expected)}")
            all_pass = False
    print("\nAll assertions:", "PASS" if all_pass else "FAIL")
    assert all_pass, "heading assertions failed"

    # excerpt smoke check
    sample = ('It is a truth universally acknowledged, that a single man in possession '
              'of a good fortune must be in want of a wife. However little known the '
              'feelings or views of such a man may be on his first entering a neighbourhood, '
              'this truth is so well fixed in the minds of the surrounding families.')
    ex = build_excerpt(sample)
    last = ex.rstrip("…")[-1]
    assert last in '.!?""”', f"excerpt ends mid-word: {repr(ex[-20:])}"
    print(f"\nexcerpt smoke: {repr(ex[:80])} ... OK")

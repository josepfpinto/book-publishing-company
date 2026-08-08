"""Unit tests for the citation composition layer.

Pure-function coverage for `compose_heading()`, `build_excerpt()` and
`populate_excerpts()` — no fixtures, no book HTML, no network. Complements
`test_ingestion.py`, which is the integration gate and exercises the same
code against real parsed chapters.

Migrated from the `__main__` assertion block that previously lived inside
`core/citations.py`, where nothing ever ran it.
"""
from __future__ import annotations

import pytest

from core.citations import build_excerpt, compose_heading, populate_excerpts

# Terminal punctuation an excerpt may end on: the sentence-splitter class in
# citations.py plus the truncation ellipsis.
_TERMINAL = '.!?”"…'

_PP_OPENING = (
    "It is a truth universally acknowledged, that a single man in possession "
    "of a good fortune must be in want of a wife. However little known the "
    "feelings or views of such a man may be on his first entering a "
    "neighbourhood, this truth is so well fixed in the minds of the "
    "surrounding families."
)


# ---------------------------------------------------------------------------
# compose_heading — plan §4 Citation schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("chapter_number", "chapter_title", "page_start", "page_end", "expected"),
    [
        pytest.param(
            9, "Meg Goes to Vanity Fair", None, None,
            "Chapter 9 — Meg Goes to Vanity Fair",
            id="real-title-no-pages",
        ),
        pytest.param(
            26, "Chapter 26", "182", "183",
            "Chapter 26 · pp. 182–183",
            id="fallback-title-page-range",
        ),
        pytest.param(
            26, "Chapter 26", "182", None,
            "Chapter 26 · p. 182",
            id="fallback-title-single-page",
        ),
        pytest.param(
            26, "Chapter 26", None, None,
            "Chapter 26",
            id="fallback-title-no-pages",
        ),
    ],
)
def test_canonical_headings(chapter_number, chapter_title, page_start, page_end, expected):
    """The four canonical forms named in plan §4 and phase-3 tasks.md."""
    assert compose_heading(chapter_number, chapter_title, page_start, page_end) == expected


def test_real_title_combines_with_page_range():
    """Title and page clauses are additive — Little Women with page metadata."""
    assert (
        compose_heading(9, "Meg Goes to Vanity Fair", "150", "152")
        == "Chapter 9 — Meg Goes to Vanity Fair · pp. 150–152"
    )


def test_identical_start_and_end_page_uses_singular_form():
    assert compose_heading(26, "Chapter 26", "182", "182") == "Chapter 26 · p. 182"


def test_end_page_without_start_page_is_dropped():
    """An end page with no start page is meaningless — degrade to the base form."""
    assert compose_heading(26, "Chapter 26", None, "183") == "Chapter 26"


def test_fallback_title_is_suppressed_only_on_exact_match():
    """Suppression is exact string equality, not a prefix match.

    'Chapter 26.' (trailing period) is a real title and must survive.
    """
    assert compose_heading(26, "Chapter 26.", None, None) == "Chapter 26 — Chapter 26."


def test_separators_use_the_exact_typographic_codepoints():
    """Em dash, middle dot and en dash are visually near-identical to their
    ASCII lookalikes and break silently if an editor normalises them."""
    heading = compose_heading(9, "Meg Goes to Vanity Fair", "150", "152")
    assert "—" in heading, "title separator must be an em dash (—), not a hyphen"
    assert "·" in heading, "page separator must be a middle dot (·), not a period"
    assert "–" in heading, "page range must use an en dash (–), not a hyphen"


# ---------------------------------------------------------------------------
# build_excerpt — plan §4 Excerpt rule
# ---------------------------------------------------------------------------


def test_excerpt_stops_at_the_first_sentence_over_the_minimum():
    assert build_excerpt(_PP_OPENING) == (
        "It is a truth universally acknowledged, that a single man in possession "
        "of a good fortune must be in want of a wife.…"
    )


def test_excerpt_never_ends_mid_word():
    assert build_excerpt(_PP_OPENING).rstrip("…")[-1] in _TERMINAL


def test_excerpt_accumulates_until_the_minimum_is_reached():
    """A first sentence shorter than `minimum` pulls in the following one."""
    text = (
        "She sat down. He waited for her to speak of the matter at hand, "
        "and she did not stir. Then the door closed."
    )
    assert build_excerpt(text) == (
        "She sat down. He waited for her to speak of the matter at hand, "
        "and she did not stir.…"
    )


def test_no_ellipsis_when_the_excerpt_is_the_whole_text():
    text = "A single sentence that comfortably clears the eighty character minimum all on its own."
    assert build_excerpt(text) == text


def test_text_shorter_than_the_minimum_is_returned_whole():
    assert build_excerpt("Too short.") == "Too short."


def test_empty_text_yields_an_empty_excerpt():
    assert build_excerpt("") == ""


def test_minimum_is_configurable():
    assert build_excerpt("One. Two. Three. Four. Five. Six.", minimum=1) == "One.…"


def test_long_sentence_is_emitted_whole_rather_than_truncated():
    """There is no upper bound: cutting a long sentence would break the
    'at least one complete sentence' contract (plan §4 Excerpt rule)."""
    sentence = "She said " + "and then some more words " * 20 + "at last."
    assert build_excerpt(sentence) == sentence


def test_abbreviation_split_does_not_truncate_below_the_minimum():
    """Regression — six P&P chapters opened with 'Mr.'/'MR.'.

    The splitter treats the period in an abbreviation as a sentence boundary,
    so the first fragment is 3 chars. Accumulation must continue past it
    instead of emitting 'Mr.…' as the whole excerpt.

    Verbatim opening of P&P chapter 6 — the fragment following "Mr." is 308
    chars, which is what tripped the old length guard.
    """
    text = (
        "Mr. Darcy stood near them in silent indignation at such a mode of "
        "passing the evening, to the exclusion of all conversation, and was too "
        "much engrossed by his own thoughts to perceive that Sir William Lucas "
        "was his neighbour, till Sir William thus began:— “What a charming "
        "amusement for young people this is, Mr. Darcy!”"
    )
    excerpt = build_excerpt(text)
    assert excerpt.startswith("Mr. Darcy stood near them")
    assert len(excerpt.rstrip("…")) >= 80, f"excerpt truncated below minimum: {excerpt!r}"


# ---------------------------------------------------------------------------
# populate_excerpts
# ---------------------------------------------------------------------------


def test_populate_excerpts_mutates_in_place_and_returns_the_same_list():
    chunks = [{"text": _PP_OPENING, "excerpt": ""}]
    result = populate_excerpts(chunks)
    assert result is chunks
    assert chunks[0]["excerpt"] == build_excerpt(_PP_OPENING)
    assert chunks[0]["text"] == _PP_OPENING, "source text must not be modified"


def test_populate_excerpts_overwrites_a_pre_existing_value():
    chunks = [{"text": "Stale placeholders must not survive.", "excerpt": "stale"}]
    populate_excerpts(chunks)
    assert chunks[0]["excerpt"] == "Stale placeholders must not survive."


def test_populate_excerpts_handles_every_chunk():
    chunks = [{"text": f"Chunk {i} body text.", "excerpt": ""} for i in range(3)]
    populate_excerpts(chunks)
    assert [c["excerpt"] for c in chunks] == [f"Chunk {i} body text." for i in range(3)]

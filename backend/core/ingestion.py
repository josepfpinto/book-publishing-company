"""HTML parser and chapter-aware chunker for Project Gutenberg books.

Implements all six DOM-defect fixes documented in plan §4.
Parser logic translated directly from docs/tasks/editorial-ai-poc.parser-probe.py.
"""
from __future__ import annotations

import re
from bs4 import BeautifulSoup

ROMAN_VALS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _roman(s: str) -> int:
    s = s.upper()
    total = 0
    for i, c in enumerate(s):
        v = ROMAN_VALS[c]
        total += -v if i + 1 < len(s) and ROMAN_VALS[s[i + 1]] > v else v
    return total


def _load(html_path: str) -> BeautifulSoup:
    soup = BeautifulSoup(open(html_path, encoding="utf-8").read(), "lxml")
    # strip Project Gutenberg licence blocks (defect 4 backstop)
    for sid in ("pg-header", "pg-footer"):
        node = soup.find(id=sid)
        if node:
            node.decompose()
    return soup


def _chapters_lw(soup: BeautifulSoup) -> list[tuple]:
    """LW: anchor lives in the <p class="h2"> after <h2>; title in sibling p.h2a."""
    out = []
    for p in soup.find_all("p", class_="h2"):
        a = p.find("a")
        if not a or not re.match(r"^[IVXLC]+$", a.get("id") or ""):
            continue
        num = a["id"]
        title = ""
        nxt = p.find_next_sibling("p")
        if nxt and nxt.get("class") and "h2a" in nxt.get("class"):
            title = nxt.get_text(" ", strip=True).strip(" .").title()
        out.append((_roman(num), num, title, p))
    return out


def _chapters_pp(soup: BeautifulSoup) -> list[tuple]:
    """P&P: anchor lives inside <h2> as <a id="CHAPTER_XIII">."""
    out = []
    for h in soup.find_all("h2"):
        for a in h.find_all("a"):
            m = re.match(r"^CHAPTER_([IVXLC]+)$", a.get("id") or "", re.I)
            if m:
                out.append((_roman(m.group(1)), m.group(1).upper(), "", h))
                break
    return out


def _clean_text(node) -> str:
    """Extract narrative text from a <p>, honouring all six DOM defect fixes."""
    probe = BeautifulSoup(str(node), "lxml")
    # defect 2: drop-cap recovery — <span class="letra"><img alt="M"> → "M"
    for sp in probe.select("span.letra"):
        img = sp.find("img")
        if img and img.get("alt"):
            sp.replace_with(img["alt"])
    # defect 1: page numbers are metadata — decompose with NO whitespace inserted
    for sp in probe.select("span.pagenum"):
        sp.decompose()
    # defect 3: illustration captions are not narrative
    for sp in probe.select("span.caption, div.caption"):
        sp.decompose()
    txt = probe.get_text()
    return re.sub(r"\s+", " ", txt).strip()


def _collect(soup: BeautifulSoup, chapters: list[tuple]) -> list[dict]:
    """Walk from each chapter marker to the next, gathering paragraph-level dicts.

    Each paragraph tuple is (text, in_blockquote, para_pages) where para_pages
    holds only the pagenum spans found within that specific <p> element — not the
    chapter-aggregate. This gives chunk_book() chunk-accurate page ranges.
    """
    SKIP_CLASSES = {"h2", "h2a", "h3", "caption", "pagenum", "toc"}
    results = []
    for i, (n, numeral, title, marker) in enumerate(chapters):
        stop = chapters[i + 1][3] if i + 1 < len(chapters) else None
        paras: list[tuple[str, bool, list[str]]] = []  # (text, in_blockquote, para_pages)
        cur = marker
        while True:
            cur = cur.find_next(["p", "h2"])
            if cur is None or cur is stop:
                break
            # defect 4: any <h2> ends the chapter (catches back-matter too)
            if cur.name == "h2":
                break
            cls = set(cur.get("class") or [])
            if cls & SKIP_CLASSES:
                continue
            if cur.find_parent(class_="caption"):
                continue
            # collect pages from THIS paragraph only (not chapter-wide)
            para_pages = [
                s.get_text(strip=True).strip("{}")
                for s in cur.find_all("span", class_="pagenum")
            ]
            in_quote = cur.find_parent(["blockquote"]) or cur.find_parent(
                class_="blockquot"
            )
            txt = _clean_text(cur)
            if not txt:
                continue
            # defect 6: p.nind without drop cap = paragraph continuation
            is_cont = "nind" in cls and not cur.find(class_="letra")
            if is_cont and paras:
                prev_text, prev_quote, prev_pages = paras[-1]
                paras[-1] = (prev_text + " " + txt, prev_quote, prev_pages + para_pages)
            else:
                paras.append((txt, bool(in_quote), para_pages))
        results.append(
            {
                "n": n,
                "numeral": numeral,
                "title": title,
                "paras": paras,
            }
        )
    return results


def parse_book(html_path: str, book_id: str, book_title: str) -> list[dict]:
    """Parse HTML and return paragraph-level dicts for the given book.

    Each dict: {book_id, book_title, chapter_number, chapter_title,
                page_numbers (list), text, in_blockquote}
    """
    soup = _load(html_path)
    if book_id == "little_women":
        chapters = _chapters_lw(soup)
    else:
        chapters = _chapters_pp(soup)

    chapter_data = _collect(soup, chapters)
    paragraphs: list[dict] = []
    for ch in chapter_data:
        chapter_title = ch["title"] if ch["title"] else f"Chapter {ch['n']}"
        for text, in_blockquote, para_pages in ch["paras"]:
            paragraphs.append(
                {
                    "book_id": book_id,
                    "book_title": book_title,
                    "chapter_number": ch["n"],
                    "chapter_title": chapter_title,
                    "para_pages": para_pages,
                    "text": text,
                    "in_blockquote": in_blockquote,
                }
            )
    return paragraphs


def chunk_book(
    paragraphs: list[dict],
    chunk_chars: int = 2000,
    overlap_chars: int = 320,
) -> list[dict]:
    """Pack paragraphs into chunks of ~chunk_chars with trailing overlap.

    Never splits a paragraph across chunks. Overlap re-includes the trailing
    complete paragraph(s) from the prior chunk up to overlap_chars.
    """
    if not paragraphs:
        return []

    chunks: list[dict] = []
    # group by chapter so chunks never cross chapter boundaries
    chapters: dict[tuple, list[dict]] = {}
    for p in paragraphs:
        key = (p["book_id"], p["chapter_number"])
        chapters.setdefault(key, []).append(p)

    for (book_id, ch_num), ch_paras in chapters.items():
        meta = ch_paras[0]
        chunk_index = 0
        overlap_paras: list[dict] = []  # trailing paragraphs from prior chunk

        i = 0
        while i < len(ch_paras):
            # start each chunk with overlap paragraphs from the prior chunk
            current: list[dict] = list(overlap_paras)
            current_text_len = sum(len(p["text"]) for p in current)
            seen_pages: list[str] = []
            contains_letter = any(p["in_blockquote"] for p in current)

            # accumulate paragraphs until we reach the target size
            while i < len(ch_paras):
                p = ch_paras[i]
                current.append(p)
                current_text_len += len(p["text"])
                if p["in_blockquote"]:
                    contains_letter = True
                i += 1
                if current_text_len >= chunk_chars:
                    break

            # collect pages that appear in this chunk's paragraphs (per-para, not chapter-wide)
            all_pages: list[str] = []
            for p in current:
                all_pages.extend(p["para_pages"])
            # de-duplicate while preserving order
            seen_set: set[str] = set()
            for pg in all_pages:
                if pg not in seen_set:
                    seen_pages.append(pg)
                    seen_set.add(pg)

            chunk_text = " ".join(p["text"] for p in current).strip()

            chunk: dict = {
                "text": chunk_text,
                "book_id": book_id,
                "book_title": meta["book_title"],
                "chapter_number": ch_num,
                "chapter_title": meta["chapter_title"],
                "chunk_index": chunk_index,
                "contains_letter": contains_letter,
                "excerpt": "",
            }
            # page metadata — P&P only; omit keys entirely for LW (never write None)
            if seen_pages:
                chunk["page_start"] = seen_pages[0]
                if len(seen_pages) > 1 and seen_pages[-1] != seen_pages[0]:
                    chunk["page_end"] = seen_pages[-1]

            chunks.append(chunk)
            chunk_index += 1

            # build overlap: trailing paragraphs from current that sum <= overlap_chars
            overlap_paras = []
            overlap_len = 0
            for p in reversed(current):
                if overlap_len + len(p["text"]) > overlap_chars:
                    break
                overlap_paras.insert(0, p)
                overlap_len += len(p["text"])

    return chunks


def ingest_book(html_path: str, book_id: str, book_title: str) -> list[dict]:
    """Parse + chunk a book. Sets excerpt: '' as placeholder (citations.py fills it)."""
    paragraphs = parse_book(html_path, book_id, book_title)
    return chunk_book(paragraphs)


if __name__ == "__main__":
    import pathlib

    BASE = pathlib.Path(__file__).parent.parent.parent / "books shared"

    for path, bid, btitle, expected_chapters in [
        (BASE / "little_women.html", "little_women", "Little Women", 47),
        (
            BASE / "pride_prejudice.html",
            "pride_prejudice",
            "Pride and Prejudice",
            61,
        ),
    ]:
        chunks = ingest_book(str(path), bid, btitle)
        actual_chapters = len({c["chapter_number"] for c in chunks})
        total = len(chunks)
        assert actual_chapters == expected_chapters, (
            f"{btitle}: got {actual_chapters} chapters, expected {expected_chapters}"
        )
        print(f"{btitle}: {actual_chapters} chapters OK | {total} chunks")

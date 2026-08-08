"""Validation probe: prove the HTML-aware extraction strategy on both books.

Not production code — this exists to de-risk Phase 3 before ingestion.py is written.
"""
from bs4 import BeautifulSoup
import re, sys

VALS = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}


def roman(s):
    s = s.upper(); t = 0
    for i, c in enumerate(s):
        v = VALS[c]
        t += -v if i + 1 < len(s) and VALS[s[i + 1]] > v else v
    return t


def load(path):
    soup = BeautifulSoup(open(path, encoding='utf-8').read(), "lxml")
    # 1. Strip Project Gutenberg boilerplate (header licence block + footer licence)
    for sid in ("pg-header", "pg-footer"):
        n = soup.find(id=sid)
        if n:
            n.decompose()
    return soup


def harvest_pages(soup):
    """Pull print page numbers out of the DOM, then remove the spans.

    MUST run before any get_text(): the spans sit mid-word ("con{183}scious").
    Returns a map id(tag) -> page label for the tag each pagenum was found under.
    """
    pages = []
    for s in soup.find_all("span", class_="pagenum"):
        label = s.get_text(strip=True).strip("{}")
        pages.append((s, label))
    return pages


def clean_text(node):
    """Extract narrative text from a <p>, honouring HTML semantics."""
    probe = BeautifulSoup(str(node), "lxml")
    # drop-cap recovery: <span class="letra"><img alt="M"></span>R. BENNET -> MR. BENNET
    for sp in probe.select("span.letra"):
        img = sp.find("img")
        if img and img.get("alt"):
            sp.replace_with(img["alt"])
    # page numbers are metadata, not prose — remove with NO whitespace inserted
    for sp in probe.select("span.pagenum"):
        sp.decompose()
    # illustration captions are not passages in the book
    for sp in probe.select("span.caption, div.caption"):
        sp.decompose()
    txt = probe.get_text()
    return re.sub(r'\s+', ' ', txt).strip()


def chapters_pp(soup):
    """P&P: anchor lives inside <h2> as <a id="CHAPTER_XIII">."""
    out = []
    for h in soup.find_all("h2"):
        for a in h.find_all("a"):
            m = re.match(r'^CHAPTER_([IVXLC]+)$', a.get("id") or "", re.I)
            if m:
                out.append((roman(m.group(1)), m.group(1).upper(), "", h))
                break
    return out


def chapters_lw(soup):
    """LW: anchor lives in the <p class="h2"> after <h2>; title in <h2> and p.h2a."""
    out = []
    for p in soup.find_all("p", class_="h2"):
        a = p.find("a")
        if not a or not re.match(r'^[IVXLC]+$', a.get("id") or ""):
            continue
        num = a["id"]
        title = ""
        nxt = p.find_next_sibling("p")
        if nxt and nxt.get("class") and "h2a" in nxt.get("class"):
            title = nxt.get_text(" ", strip=True).strip(" .").title()
        out.append((roman(num), num, title, p))
    return out


def collect(soup, chapters):
    """Walk from each chapter marker to the next, gathering paragraphs."""
    SKIP_CLASSES = {"h2", "h2a", "h3", "caption", "pagenum", "toc"}
    results = []
    for i, (n, numeral, title, marker) in enumerate(chapters):
        stop = chapters[i + 1][3] if i + 1 < len(chapters) else None
        paras, pages, letters = [], [], 0
        cur = marker
        while True:
            cur = cur.find_next(["p", "h2"])
            if cur is None or cur is stop:
                break
            # ANY <h2> ends the chapter — the next chapter's heading, or, for the
            # final chapter, the back matter ("The Works of...", Transcriber's Notes).
            if cur.name == "h2":
                break
            cls = set(cur.get("class") or [])
            if cls & SKIP_CLASSES:
                continue
            # illustration caption blocks
            if cur.find_parent(class_="caption"):
                continue
            for s in cur.find_all("span", class_="pagenum"):
                pages.append(s.get_text(strip=True).strip("{}"))
            in_quote = cur.find_parent(["blockquote"]) or cur.find_parent(class_="blockquot")
            txt = clean_text(cur)
            if not txt:
                continue
            # p.nind without a drop cap = paragraph continued across an illustration
            is_cont = "nind" in cls and not cur.find(class_="letra")
            if is_cont and paras:
                paras[-1] = (paras[-1][0] + " " + txt, paras[-1][1])
            else:
                paras.append((txt, bool(in_quote)))
            if in_quote:
                letters += 1
        results.append(dict(n=n, numeral=numeral, title=title, paras=paras,
                            pages=pages, letters=letters))
    return results


def report(name, path, chapter_fn, expected):
    soup = load(path)
    chs = chapter_fn(soup)
    data = collect(soup, chs)
    print(f"\n{'='*66}\n{name}  ({path})\n{'='*66}")
    print(f"chapters: {len(data)} (expected {expected}) "
          f"{'OK' if len(data)==expected else '** MISMATCH **'}")
    print(f"sequential: {[d['n'] for d in data]==list(range(1,expected+1))}")
    total_chars = sum(len(t) for d in data for t, _ in d["paras"])
    print(f"paragraphs: {sum(len(d['paras']) for d in data)}  "
          f"chars: {total_chars//1000}k  approx tokens: {total_chars//4//1000}k")
    print(f"chapters with descriptive title: {sum(1 for d in data if d['title'])}/{len(data)}")
    print(f"chapters with print pages: {sum(1 for d in data if d['pages'])}/{len(data)}")
    print(f"quoted/letter paragraphs: {sum(d['letters'] for d in data)}")

    # ---- assertions that catch every defect found in the DOM survey ----
    fails = []
    if len(data) != expected:
        fails.append(f"chapter count {len(data)} != {expected}")
    leak = [(d['n'], t[:60]) for d in data for t, _ in d["paras"]
            if re.search(r'\{[\divxlcIVXLC]+\}', t)]
    if leak:
        fails.append(f"pagenum leakage in {len(leak)} paras e.g. {leak[0]}")
    BAD = ("The Works of Louisa May Alcott", "Transcriber's Note", "Project Gutenberg",
           "START OF THE PROJECT")
    bm = [(d['n'], b) for d in data for t, _ in d["paras"] for b in BAD if b in t]
    if bm:
        fails.append(f"back-matter leakage: {bm[:2]}")
    bad_open = [(d['n'], d['paras'][0][0][:40]) for d in data
                if d['paras'] and not d['paras'][0][0][:1].isupper()
                and not d['paras'][0][0][:1] in '“"\'']
    if bad_open:
        fails.append(f"chapter opens lowercase (drop-cap loss?): {bad_open[:3]}")
    print("\nASSERTIONS:", "ALL PASS" if not fails else "FAILURES")
    for f in fails:
        print("  FAIL:", f)

    d = data[1]
    print(f"\nsample — ch {d['n']} '{d['title'] or '(untitled)'}' "
          f"pages {d['pages'][:1]}..{d['pages'][-1:]}")
    print("  opens:", repr(d["paras"][0][0][:110]))
    return data


BASE = "/Users/josepedropinto/Desktop/Repo/agentic-book-publishing-company-workspace/book-publishing-company/books shared/"
lw = report("Little Women", BASE + "little_women.html", chapters_lw, 47)
pp = report("Pride & Prejudice", BASE + "pride_prejudice.html", chapters_pp, 61)


# ---------------------------------------------------------------- citations
import textwrap
SENT = re.compile(r'(?<=[.!?”"])\s+')

def excerpt(text, target=230, minimum=80):
    """>= 1 complete sentence, never cut mid-word, ellipsis only if truncated."""
    sents = SENT.split(text)
    out = ""
    for s in sents:
        if out and len(out) + len(s) + 1 > target:
            break
        out = (out + " " + s).strip()
        if len(out) >= minimum:
            break
    if not out:
        out = text[:target].rsplit(" ", 1)[0]
    return out + ("…" if len(out) < len(text.strip()) else "")


def cite(book_title, d, chunk_pages):
    """Compose the SourceCard heading line with graceful degradation."""
    head = f"Chapter {d['n']}"
    if d["title"]:
        head += f" — {d['title']}"
    if chunk_pages:
        head += f" · p. {chunk_pages[0]}" if len(set(chunk_pages)) == 1 \
                else f" · pp. {chunk_pages[0]}–{chunk_pages[-1]}"
    return book_title, head


print("\n\n" + "="*66 + "\nSIMULATED SOURCE CARDS\n" + "="*66)
for book_title, data in (("Little Women", lw), ("Pride & Prejudice", pp)):
    for d in (data[0], data[25]):
        b, h = cite(book_title, d, d["pages"][:2])
        body = excerpt(d["paras"][0][0])
        print(f"\n  {b.upper()}")
        print(f"  {h}")
        for line in textwrap.wrap(f'"{body}"', 62):
            print(f"    {line}")

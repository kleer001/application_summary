"""Check a reader's output against the slice it was given.

A value survives only if its quote occurs on the page it cites. A value the
reader wrote as a JSON number must additionally have its digits present in its
own quote, which is the guard against a vision model smoothing a figure toward a
rounder one.

The guard covers numbers, not everything numeric-looking. A figure recorded with
its unit or currency — `"660 m²"`, `"$69,700.00"` — is a string and is checked
only by its quote, and a third of the entries in the area and amount fields are
written that way. That is deliberate: the contract asks for the document's own
words, and a reader that keeps the unit is following it. The quote check still
has to pass, so such a value cannot be invented; what it can be is rounded
without the digits being compared.
"""
import functools, json, re, sys
from collections import Counter
from typing import NamedTuple

from norm import norm, on_page, tokens

NULL_REASONS = ("not_stated", "blank_on_form", "redacted", "illegible")

# The verdicts this module mints, named so consumers stop re-spelling them.
# VERIFIED is "the quote was found where it said it would be" — QUEUE is a pass
# with a caveat about a page break, not a failure. FAILED is the pair that means
# the answer cannot be shown on its page and must not reach a cell.
VERIFIED = ("pass", "QUEUE")
FAILED = ("REJECT", "MALFORMED")


# How far in from a page edge furniture can reach. Only a run of furniture
# unbroken from the edge is stripped, so looking too far costs nothing: the first
# line of real text stops the walk.
EDGE = 6


class Page(NamedTuple):
    """One page, folded once, in the three shapes the checks ask for.

    `folded` and `tokens` are the whole page and are what a citation to this page
    is tested against. The other two are the page with its furniture removed, and
    exist only to join two pages at a break: `without_footer` where this page is
    the first half of the seam, `without_header` where it is the second.
    """
    folded: str
    tokens: set
    without_footer: str
    without_header: str


def shape(line):
    """A line with every number standing for any number.

    Furniture is not a phrase to match. A Bates stamp, a page number, a margin
    column of section numbers and a file-number header differ page to page in
    their digits and in nothing else, so the digits are what has to go before the
    lines can be seen to be the same line.
    """
    return re.sub(r"[^a-z#]+", "", re.sub(r"\d+", "#", line.lower()))


def only_numbers(sh):
    """A line that is a number and nothing else.

    A Bates stamp, a page number and the margin column of section numbers the
    scanner reads before the prose all fold to this. None of them is prose, and
    at a page edge none of them is ever part of a requirement's own text.

    Not decided by recurrence, because the margin column is not a running
    header: it appears on the pages whose numbering happens to spill and on no
    others, which is too few pages to recur and is still furniture.
    """
    return bool(sh) and set(sh) == {"#"}


def furniture(pages):
    """The shapes that recur at the top and at the bottom of this document.

    Found by recurrence rather than by pattern, so the press's own furniture is
    caught whatever it is and nothing has to be named. A shape counts as
    furniture when it sits at the same edge of at least a third of the pages, and
    of at least two: one page's habit is not a running header.

    Counted per page, not per line, so that many copies of one shape on a single
    page cannot vote themselves into the set.

    A redaction marker — `s.19(1)`, `s.20(1)(b)` — is deliberately not caught.
    It carries letters, so it needs recurrence, and it is stamped where content
    was withheld rather than on every page, so it does not recur. That is the
    wanted answer and not a gap: the marker exists to say something was removed,
    and joining two pages across one would assert a continuity the document
    itself denies. A condition that straddles a redaction belongs in the queue.
    """
    heads, tails = Counter(), Counter()
    for lines in pages.values():
        heads.update({shape(l) for l in lines[:EDGE] if shape(l)})
        tails.update({shape(l) for l in lines[-EDGE:] if shape(l)})
    floor = max(2, -(-len(pages) // 3))
    return ({k for k, n in heads.items() if n >= floor},
            {k for k, n in tails.items() if n >= floor})


def strip_edges(lines, head_shapes, tail_shapes):
    """The page's body: the run of furniture at each edge walked off."""
    def furn(line, shapes):
        sh = shape(line)
        return sh in shapes or only_numbers(sh)

    i, j = 0, len(lines)
    while i < j and furn(lines[i], head_shapes):
        i += 1
    while j > i and furn(lines[j - 1], tail_shapes):
        j -= 1
    return lines[i:j]


@functools.lru_cache(maxsize=8)
def load_pages(slice_path):
    """Page number to text, and to folded text, folded once per document."""
    text = open(slice_path, encoding="utf-8").read()
    pages = {int(m.group(1)): m.group(2) for m in
             re.finditer(r"=== page (\d+) ===\n(.*?)(?=\n\n=== page |\Z)", text, re.S)}
    lines = {p: [l for l in t.split("\n") if l.strip()] for p, t in pages.items()}
    head_shapes, tail_shapes = furniture(lines)
    # Each edge is walked off on its own: a page is the first half of one seam
    # and the second half of another, and in each role it keeps the edge that is
    # not the seam.
    return {p: Page(norm(t), set(tokens(t)),
                    norm("".join(strip_edges(lines[p], set(), tail_shapes))),
                    norm("".join(strip_edges(lines[p], head_shapes, set()))))
            for p, t in pages.items()}


def page_of(folded, pg):
    """The page, or an empty one where the document has no such page."""
    return folded.get(pg) or Page("", set(), "", "")


def digits_present(value, quote):
    """Every digit-run of the value must appear in the quote, separators aside.

    Applied only where the reader wrote a JSON number; see the module docstring
    for why a value carrying its unit is checked by its quote alone.
    """
    want = re.sub(r"[^\d]", "", str(value).split(".")[0])
    return want in re.sub(r"[^\d]", "", quote) if want else True


def check_field(name, f, folded, n):
    """Every field is a list of entries and is only as good as they are."""
    if not isinstance(f, dict):
        return (name, "MALFORMED", "field is not an object")
    entries = f.get("entries")
    if entries is None:
        return (name, "MALFORMED", "no entries key")
    if not isinstance(entries, list):
        return (name, "MALFORMED", "entries is not a list")

    if not entries:
        reason = f.get("reason")
        if reason not in NULL_REASONS:
            return (name, "MALFORMED", f"no entries and no usable reason ({reason!r})")
        return (name, "null", reason)

    bad, queued, loose = [], 0, 0
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            bad.append(f"[{i}] not an object")
            continue
        v, q, pg = e.get("value"), e.get("quote"), e.get("page")
        if v in (None, ""):
            bad.append(f"[{i}] entry with no value")
        elif not isinstance(v, (str, int, float)) or isinstance(v, bool):
            # A value is a thing the page says, and a cell holds one. An object
            # or a list is neither: it reaches the workbook writer intact and
            # fails there, after the build has done all its work. Caught here so
            # it is queued like any other unusable answer.
            bad.append(f"[{i}] value is {type(v).__name__}, not text")
        elif not q:
            bad.append(f"[{i}] value with no quote")
        elif not isinstance(pg, int) or not (1 <= pg <= n):
            bad.append(f"[{i}] page {pg} outside 1-{n}")
        elif not (how := on_page(q, *page_of(folded, pg)[:2])):
            # A quote marked `image` is a claim that the text layer does not
            # carry it. Finding the same words on another page of that layer does
            # not refute the claim — a short phrase like a job title recurs, and
            # the signature block it was read from can be mangled on the page it
            # really sits on. So the wrong-page test is asked only of a quote
            # that says it came from the text.
            nq = norm(q)
            hit = (None if e.get("source") == "image" else
                   next((p for p, pf in folded.items() if nq in pf.folded), None))
            if hit:
                bad.append(f"[{i}] quote is on page {hit}, cited {pg}")
            elif e.get("source") == "image":
                queued += 1
            else:
                bad.append(f"[{i}] quote not found in the excerpt")
        elif how == "ocr":
            loose += 1
        elif isinstance(v, (int, float)) and not digits_present(v, q):
            bad.append(f"[{i}] value {v} digits absent from its own quote")

    if bad:
        return (name, "REJECT",
                f"{len(entries) - len(bad)}/{len(entries)} entries: " + "; ".join(bad[:3]))
    if queued:
        return (name, "QUEUE", f"{queued}/{len(entries)} read from the scan, not in the text")
    note = f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}"
    return (name, "pass", note + (f", {loose} matched past OCR damage" if loose else ""))


def looks_truncated(text, page_folded):
    """A condition that stops exactly where its page stops.

    Its last words sitting at the very foot of the page, with no full stop, is
    what a requirement cut at the page break looks like. It is a signal, not a
    verdict: some conditions genuinely end there.
    """
    t = str(text or "").strip()
    if len(t) < 20 or t[-1:] in '.;:)"':
        return False
    tail = norm(t)[-40:]
    return bool(tail) and tail in page_folded[-90:]


def on_cited_page(text, folded, pg):
    """Is this text on the page it cites, allowing for a page break?

    A condition may run past the foot of its page, so exact containment is
    offered the cited page joined to the one after: a requirement that genuinely
    straddles a break is still quoted whole, and the match must cross the seam to
    succeed. The fuzzy fallback is not offered the join. Its threshold was
    measured against the words of one page, and handing it two roughly doubles
    the pool it can draw on to clear the bar.

    That difference is not theoretical. Measured over the corpus, of the
    conditions that failed their own page and passed the two-page test, two
    crossed the seam and forty cleared the bar only on the doubled pool — a page
    citation established by nothing but the neighbouring page's vocabulary.

    The two halves are joined body to body, because what sits between them on the
    page is not prose: the foot of one page carries a page number and a Bates
    stamp, and the head of the next carries a running file-number header and the
    margin column of section numbers the scanner reads before the text. A
    sentence broken across the seam does not survive having them spliced into its
    middle. Each page keeps the edge that is not the seam, so a citation to a
    page is still tested against that page whole.
    """
    here, nxt = page_of(folded, pg), page_of(folded, pg + 1)
    return on_page(text, here.without_footer + nxt.without_header, here.tokens)


def check_conditions(doc, slice_path):
    """Every numbered condition's text, against the page it starts on."""
    folded = load_pages(slice_path)
    rows = []
    for c in doc.get("conditions", []) or []:
        num, pg, text = c.get("number"), c.get("page"), c.get("text")
        if not text:
            rows.append((num, "REJECT", "condition with no text"))
        elif not isinstance(pg, int) or pg not in folded:
            rows.append((num, "REJECT", f"page {pg} is not a page of this document"))
        else:
            how = on_cited_page(text, folded, pg)
            if not how:
                rows.append((num, "REJECT", "text not established on the page it cites"))
            elif looks_truncated(text, folded[pg][0]):
                rows.append((num, "QUEUE", "ends at the foot of its page, mid-sentence"))
            else:
                rows.append((num, "pass", how))
    return rows


def check(doc, slice_path, first, last):
    """Every field of one already-loaded reader output."""
    folded, n = load_pages(slice_path), last - first + 1
    return [check_field(name, f, folded, n) for name, f in doc.get("fields", {}).items()]


def verdicts_for(doc, slice_path, first, last):
    """field name -> verdict, which is what callers combining readers need."""
    return {name: verdict for name, verdict, _ in check(doc, slice_path, first, last)}


if __name__ == "__main__":
    out, sl, lo, hi = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    rows = check(json.load(open(out)), sl, lo, hi)
    order = {"REJECT": 0, "MALFORMED": 0, "QUEUE": 1, "pass": 2, "null": 3}
    for name, verdict, why in sorted(rows, key=lambda r: (order.get(r[1], 4), r[0])):
        print(f"  {verdict:9s} {name:30s} {why}")
    print(f"\n  {dict(Counter(v for _, v, _ in rows))}")

"""What is spliced into a condition that runs past the foot of its page?

`verify.on_cited_page` joins the cited page to the one after so a requirement
broken across the break is still matched whole. Joining the two pages raw does
not achieve that, because what sits between the two halves on the paper is not
prose: the foot of one page carries a page number and a Bates stamp, and the head
of the next carries a running file-number header and the margin column of section
numbers the scanner reads before the text. Splicing those into the middle of a
sentence defeats the containment the join exists to allow.

This is the measurement behind stripping them. It walks furniture off each side
of the seam and re-runs the cited-page check over every condition in the
workbook, reporting what the strip admits that the raw join rejected, and what it
costs.

  gained   the raw join rejected the condition, the stripped join accepts it
  lost     the raw join accepted it and the stripped join does not

`lost` is the number that governs. The strip may only remove what no requirement
quotes; a single loss means it is eating text, and the rule does not stay.

Two settings are compared, because furniture is found two ways and only one of
them is decided by recurrence:

  recurrence only   a shape counts as furniture when it sits at the same page
                    edge often enough to be the press's, not one page's habit.
                    Catches the running header and the Bates stamp.
  and bare numbers  additionally, a line that folds to a number and nothing else.
                    The margin column of section numbers appears only on the
                    pages whose numbering spills, too few to recur, and is
                    furniture regardless.

A redaction marker — `s.19(1)`, `s.20(1)(b)` — is caught by neither, which is the
wanted answer. It carries letters so it needs recurrence, and it is stamped where
content was withheld rather than on every page, so it does not recur. Joining two
pages across one would assert a continuity the document itself denies.

Run from the repository root.
"""
import functools, json, re, sys
from collections import Counter

S = "A-2020-02093-MRV-FINAL_pdf_v3"
sys.path.insert(0, S)

import openpyxl
import qc
from norm import norm, on_page, tokens
from verify import EDGE, Page, only_numbers, shape

SANDBOX = f"{S}/run2"


def pages_of(slice_path):
    text = open(slice_path, encoding="utf-8").read()
    pages = {int(m.group(1)): m.group(2) for m in
             re.finditer(r"=== page (\d+) ===\n(.*?)(?=\n\n=== page |\Z)", text, re.S)}
    return pages, {p: [l for l in t.split("\n") if l.strip()] for p, t in pages.items()}


def recurring(lines):
    heads, tails = Counter(), Counter()
    for L in lines.values():
        heads.update({shape(l) for l in L[:EDGE] if shape(l)})
        tails.update({shape(l) for l in L[-EDGE:] if shape(l)})
    floor = max(2, -(-len(lines) // 3))
    return ({k for k, n in heads.items() if n >= floor},
            {k for k, n in tails.items() if n >= floor})


def strip_edges(L, shapes_head, shapes_tail, bare_numbers):
    def furn(line, shapes):
        sh = shape(line)
        return sh in shapes or (bare_numbers and only_numbers(sh))

    i, j = 0, len(L)
    while i < j and furn(L[i], shapes_head):
        i += 1
    while j > i and furn(L[j - 1], shapes_tail):
        j -= 1
    return L[i:j]


@functools.lru_cache(maxsize=None)
def loaded(slice_path, bare_numbers):
    pages, lines = pages_of(slice_path)
    hs, ts = recurring(lines)
    return {p: Page(norm(t), set(tokens(t)),
                    norm("".join(strip_edges(lines[p], set(), ts, bare_numbers))),
                    norm("".join(strip_edges(lines[p], hs, set(), bare_numbers))))
            for p, t in pages.items()}


EMPTY = Page("", set(), "", "")


def cited(folded, text, pg, stripped):
    here, nxt = folded.get(pg) or EMPTY, folded.get(pg + 1) or EMPTY
    if stripped:
        return on_page(text, here.without_footer + nxt.without_header, here.tokens)
    return on_page(text, here.folded + nxt.folded, here.tokens)


def conditions(xlsx):
    """Every condition the sheet carries, as (slice, text, page within it, tag).

    Read off the workbook rather than off the readers, because the workbook is
    what `qc` tests and pass C may have replaced a reader's copy of the text.
    Entries read off the scan are skipped: they are not in the text layer by
    design and no join can put them there.
    """
    orders = json.load(open(f"{SANDBOX}/wave.json"))
    complete = qc.complete_stems(SANDBOX)
    ranges = {o["doc_id"]: o for o in orders if o["stem"] in complete}
    cs = openpyxl.load_workbook(xlsx, data_only=True)["Conditions"]
    cix = {c.value: i for i, c in enumerate(cs[1])}
    out = []
    for c in cs.iter_rows(min_row=2, values_only=True):
        o = ranges.get(c[cix["Document"]])
        text, pg = c[cix["Text"]], c[cix["Page"]]
        if not o or not text or not isinstance(pg, int) or c[cix["Source"]] == "image":
            continue
        out.append((o["slice"], text, pg - o["first_page"] + 1,
                    f'{c[cix["File_Number"]]} {c[cix["Number"]]} p{pg}'))
    return out


def main(xlsx):
    cases = conditions(xlsx)
    raw = {tag: cited(loaded(sl, False), text, rel, False)
           for sl, text, rel, tag in cases}
    print(f"{len(cases)} conditions, {sum(1 for v in raw.values() if v)} accepted "
          f"by the raw join\n")
    print(f"{'furniture':>18} {'accepted':>9} {'gained':>7} {'lost':>5}")
    for label, bare in (("recurrence only", False), ("and bare numbers", True)):
        gained, lost, ok = [], [], 0
        for sl, text, rel, tag in cases:
            v = cited(loaded(sl, bare), text, rel, True)
            ok += bool(v)
            if v and not raw[tag]:
                gained.append(tag)
            if raw[tag] and not v:
                lost.append(tag)
        print(f"{label:>18} {ok:>9} {len(gained):>7} {len(lost):>5}")
        for tag in lost:
            print(f"{'':>18}   lost: {tag}")
    still = [tag for sl, text, rel, tag in cases
             if not cited(loaded(sl, True), text, rel, True)]
    print("\nstill rejected, which is where a straddle across a redaction lands:")
    for tag in still:
        print(f"    {tag}")


if __name__ == "__main__":
    main(sys.argv[1])

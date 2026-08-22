"""Check a reader's output against the slice it was given.

A value survives only if its quote occurs on the page it cites. Numeric values
must additionally have their digits present in their own quote, which is the
guard against a vision model smoothing a figure toward a rounder one.
"""
import functools, json, re, sys
from collections import Counter

from norm import norm, on_page, tokens

NULL_REASONS = ("not_stated", "blank_on_form", "redacted", "illegible")

# The verdicts this module mints, named so consumers stop re-spelling them.
# VERIFIED is "the quote was found where it said it would be" — QUEUE is a pass
# with a caveat about a page break, not a failure. FAILED is the pair that means
# the answer cannot be shown on its page and must not reach a cell.
VERIFIED = ("pass", "QUEUE")
FAILED = ("REJECT", "MALFORMED")


@functools.lru_cache(maxsize=8)
def load_pages(slice_path):
    """Page number to text, and to folded text, folded once per document."""
    text = open(slice_path, encoding="utf-8").read()
    pages = {int(m.group(1)): m.group(2) for m in
             re.finditer(r"=== page (\d+) ===\n(.*?)(?=\n\n=== page |\Z)", text, re.S)}
    return {p: (norm(t), set(tokens(t))) for p, t in pages.items()}


def digits_present(value, quote):
    """Every digit-run of the value must appear in the quote, separators aside."""
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
        elif not q:
            bad.append(f"[{i}] value with no quote")
        elif not isinstance(pg, int) or not (1 <= pg <= n):
            bad.append(f"[{i}] page {pg} outside 1-{n}")
        elif not (how := on_page(q, *folded.get(pg, ("", set())))):
            nq = norm(q)
            hit = next((p for p, (ft, _) in folded.items() if nq in ft), None)
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


def check_conditions(doc, slice_path):
    """Every numbered condition's text, against the page it starts on.

    A condition may run past the foot of its page, so the text is looked for on
    the page it cites and the one after. Nothing else is admitted: a condition
    sourced from anywhere in the document would make the page citation
    decorative.
    """
    folded = load_pages(slice_path)
    rows = []
    for c in doc.get("conditions", []) or []:
        num, pg, text = c.get("number"), c.get("page"), c.get("text")
        if not text:
            rows.append((num, "REJECT", "condition with no text"))
        elif not isinstance(pg, int) or pg not in folded:
            rows.append((num, "REJECT", f"page {pg} is not a page of this document"))
        else:
            spread_f = folded[pg][0] + folded.get(pg + 1, ("", set()))[0]
            spread_t = folded[pg][1] | folded.get(pg + 1, ("", set()))[1]
            how = on_page(text, spread_f, spread_t)
            if not how:
                rows.append((num, "REJECT", "text not found on its page or the next"))
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

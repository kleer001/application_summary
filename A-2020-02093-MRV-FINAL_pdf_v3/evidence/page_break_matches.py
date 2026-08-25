"""What is a match across a page break actually resting on?

`verify.on_cited_page` lets exact containment run from the cited page into the
next one, but keeps the fuzzy fallback on the cited page's own words. This is the
measurement behind that split: it takes every condition and every field entry
that fails its own page but passes when the two pages are joined, and sorts them
by what the join is doing for them.

  wholly on the next page  the text is entirely on page N+1, cited as N. A
                           mis-citation, and the join hides it.
  crosses the seam         the folded text occurs in the join and in neither
                           page alone, so the match must span the break. The one
                           case a join legitimately exists for.
  token overlap only       neither of the above; the words are simply spread
                           across two pages' vocabulary. Joining the token sets
                           roughly doubles the pool the 90% threshold draws on,
                           and that threshold was measured against one page.

Run from the repository root.
"""
import json, os, sys
from collections import Counter

S = "A-2020-02093-MRV-FINAL_pdf_v3"
sys.path.insert(0, S)
from norm import norm, on_page
from verify import load_pages
from paths import complete_stems

SANDBOX = f"{S}/run2"
orders = {o["stem"]: o for o in json.load(open(f"{SANDBOX}/wave.json"))}


def sort_one(text, folded, pg):
    """What the join is doing for this text, or None if it is not needed."""
    here = folded.get(pg, ("", set()))
    nxt = folded.get(pg + 1, ("", set()))
    if on_page(text, *here):
        return None
    joined, pool = here[0] + nxt[0], here[1] | nxt[1]
    if not on_page(text, joined, pool):
        return None
    folded_text = norm(text)
    where = next((p for p, (ft, _) in folded.items() if folded_text in ft), None)
    if where is not None:
        return "wholly on another page — a mis-citation the join would hide"
    if folded_text in joined:
        return "crosses the seam — the case a join exists for"
    return "token overlap only — no evidence of order or location"


def sweep():
    conds, fields = Counter(), Counter()
    for stem in sorted(complete_stems(SANDBOX)):
        o = orders[stem]
        folded = load_pages(o["slice"])
        n = o["last_page"] - o["first_page"] + 1
        for tag, bucket, items in (
                ("b1", conds, "conditions"), ("b2", conds, "conditions"),
                ("a1", fields, "fields"), ("a2", fields, "fields")):
            path = f"{SANDBOX}/out/{stem}.{tag}.json"
            if not os.path.exists(path):
                continue
            doc = json.load(open(path))
            if items == "conditions":
                pairs = [(c.get("text"), c.get("page")) for c in doc.get("conditions") or []]
            else:
                pairs = [(e.get("quote"), e.get("page"))
                         for f in (doc.get("fields") or {}).values()
                         for e in (f or {}).get("entries") or []]
            for text, pg in pairs:
                if not text or not isinstance(pg, int) or not (1 <= pg <= n):
                    continue
                kind = sort_one(text, folded, pg)
                if kind:
                    bucket[kind] += 1
    return conds, fields


if __name__ == "__main__":
    conds, fields = sweep()
    for label, c in (("CONDITIONS", conds), ("FIELD ENTRIES", fields)):
        print(f"\n{label} — what the two-page join is carrying  ({sum(c.values())} of them)")
        for k, v in c.most_common():
            print(f"   {v:5d}  {k}")

"""Can a reader's `source` claim be contradicted by the evidence on disk?

A reader records source text|image|both per entry. "both" asserts it corroborated
the answer against the scan. The failure that prompted this: a read whose PDF had
errored claimed "both" on all 35 entries.

Two things are measurable per read:
  off_text  entries whose quote is NOT in the OCR layer -> the scan was used.
  glyph     entries whose value carries a glyph the OCR layer does not have at
            that spot (m2 recovered where the text says m7/m0/m*) -> scan used.
A read claiming "both" everywhere with neither signal is unfalsifiable, not
proven false. A read with either signal used the scan.
"""
import json, os, re, sys, collections
sys.path.insert(0, "A-2020-02093-MRV-FINAL_pdf_v3")
from norm import norm

S = "A-2020-02093-MRV-FINAL_pdf_v3"
wave = {o["stem"]: o for o in json.load(open(f"{S}/staged/wave.json"))}
OCR_M2 = re.compile(r"m[2²?7*°'’]", re.I)

rows = []
for name in sorted(os.listdir(f"{S}/run2/out")):
    if not name.endswith(".json"):
        continue
    stem, tag, _ = name.split(".")
    if not tag.startswith("a"):
        continue
    order = wave.get(stem)
    if not order:
        continue
    slice_txt = norm(open(order["slice"], encoding="utf-8").read())
    doc = json.load(open(f"{S}/run2/out/{name}"))
    claims = collections.Counter()
    off_text = glyph = total = 0
    for f in (doc.get("fields") or {}).values():
        for e in (f or {}).get("entries") or []:
            q = e.get("quote") or ""
            if not q:
                continue
            total += 1
            claims[e.get("source")] += 1
            if norm(q)[:60] and norm(q)[:60] not in slice_txt:
                off_text += 1
            v = str(e.get("value") or "")
            if "m²" in v or "m2" in v:
                if "m²" in v and "m²" not in norm(q) and OCR_M2.search(q or ""):
                    glyph += 1
    rows.append((name, total, claims, off_text, glyph))

both_only = [r for r in rows if r[2] and set(r[2]) <= {"both"}]
print(f"{len(rows)} pass-A reads")
print(f"{len(both_only)} claim 'both' on every entry")
unfalsifiable = [r for r in both_only if r[3] == 0 and r[4] == 0]
print(f"{len(unfalsifiable)} of those show no sign the scan was used at all:")
for r in unfalsifiable:
    print(f"   {r[0]:42s} {r[1]:3d} entries, all 'both', 0 off-text, 0 glyph")
print()
print("distribution of source claims over all pass-A entries:")
agg = collections.Counter()
for r in rows: agg.update(r[2])
for k, v in agg.most_common(): print(f"   {str(k):8s} {v}")
print()
print("reads WITH positive evidence the scan was used (off-text quotes):")
withev = [r for r in rows if r[3] > 0]
print(f"   {len(withev)} of {len(rows)}")

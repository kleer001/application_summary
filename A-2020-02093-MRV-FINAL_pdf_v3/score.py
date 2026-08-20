"""Score a wave: quote-verification, reader agreement, and agreement with the
human-filled workbook on the fields the workbook happens to carry.

The workbook is the test set and is read only here, at the top layer. Nothing
in this file is ever shown to a reader.
"""
import json, sys, os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from combine import values
from ids import FILE_RX
from norm import norm
from verify import check

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = json.load(open(os.path.join(HERE, "release.json")))["prior_summary"]

# extracted field -> workbook column, and how to compare
MAP = {
    "date_of_issuance":     ("Authorization_Date",   "date"),
    "proponent":            ("Proponent",            "text"),
    "province":             ("Province",             "text"),
    "hadd_destruction_m2":  ("HADD_Destruction_m2",  "num"),
    "hadd_alteration_m2":   ("HADD_Alteration_m2",   "num"),
    "hadd_disturbance_m2":  ("HADD_Disturbance_m2",  "num"),
    "impact_other_units":   ("HADD_Other_Units",     "text"),
}


def truth_rows():
    import openpyxl
    ws = openpyxl.load_workbook(XLSX)["Authorization_Summary"]
    hdr = [c.value for c in ws[1]]
    idx = {h: i + 1 for i, h in enumerate(hdr)}
    out = {}
    for r in range(2, ws.max_row + 1):
        m = FILE_RX.search(str(ws.cell(row=r, column=idx["DFO_File_or_PATH"]).value or ""))
        if m:
            out.setdefault(m.group(0), {h: ws.cell(row=r, column=idx[h]).value for h in hdr})
    return out


def same(kind, truth, got):
    if truth in (None, "") and got in (None, ""):
        return True
    if truth in (None, "") or got in (None, ""):
        return False
    if kind == "num":
        try:
            t, g = float(truth), float(got)
        except (TypeError, ValueError):
            return False
        return abs(t - g) <= max(1.0, t * 0.005)
    if kind == "date":
        return str(truth)[:10] == str(got)[:10]
    t, g = norm(truth), norm(got)
    return t in g or g in t


def main(sandbox, wave=None, half="tune"):
    """The work order carries the page range and the stem; do not re-derive them.

    `half` names which side of the split to score. It defaults to the tuning
    half: the holdout is scored once, at the end, and a scorer that reaches it
    by default gets run against it by accident long before then.
    """
    orders = json.load(open(wave or f"{sandbox}/wave.json"))
    if half != "all":
        keep = set(json.load(open(os.path.join(HERE, "split.json")))[half])
        orders = [o for o in orders if o["file_number"] in keep]
    truth = truth_rows()
    ver = Counter()
    agree = Counter()
    detail = []
    for order in orders:
        # one order per document: pass A, reader 1. The rest are the same document.
        if order["pass"] != "a" or order["reader"] != "1":
            continue
        doc, stem = order["file_number"], order["stem"]
        sl, lo, hi = order["slice"], order["first_page"], order["last_page"]
        for tag in ("a1", "a2"):
            p = f"{sandbox}/out/{stem}.{tag}.json"
            if not os.path.exists(p):
                detail.append((doc, tag, "MISSING OUTPUT", "", ""))
                continue
            for _, verdict, _ in check(json.load(open(p)), sl, lo, hi):
                ver[verdict] += 1
        # ground-truth agreement uses reader 1
        pa = f"{sandbox}/out/{stem}.a1.json"
        if not os.path.exists(pa) or doc not in truth:
            continue
        fields = json.load(open(pa)).get("fields", {})
        for f, (col, kind) in MAP.items():
            t = truth[doc].get(col)
            if t in (None, ""):
                continue                       # workbook has no label -> not a test case
            entries = values(fields.get(f))
            stated = [e for e in entries if e.get("role") == "total"]
            g = (stated or entries or [{}])[0].get("value")
            ok = same(kind, t, g)
            if not ok and kind == "num" and len(entries) > 1:
                # A figure the reader listed in parts still agrees with a labelled
                # total; scoring the first part alone measured the wrong thing.
                parts = [e["value"] for e in entries if isinstance(e.get("value"), (int, float))]
                if parts and (same(kind, t, sum(parts)) or any(same(kind, t, p) for p in parts)):
                    ok, g = True, f"parts{parts}"
            agree[f"{f}:{'hit' if ok else 'miss'}"] += 1
            if not ok:
                detail.append((doc, f, str(t)[:34], str(g)[:34], ""))
    print("=== quote verification (both readers, all fields) ===")
    tot = sum(ver.values())
    for k, v in ver.most_common():
        print(f"   {k:10s} {v:5d}  {v/tot:5.1%}")
    print("\n=== agreement with the human workbook (reader a) ===")
    for f in MAP:
        h, m = agree.get(f + ":hit", 0), agree.get(f + ":miss", 0)
        if h + m:
            print(f"   {f:22s} {h:2d}/{h+m:2d}  {h/(h+m):5.0%}")
    if detail:
        print("\n=== misses ===")
        for d in detail:
            print(f"   {d[0]:16s} {d[1]:22s} workbook={d[2]:36s} extracted={d[3]}")


if __name__ == "__main__":
    # score.py <sandbox> [wave.json] [tune|holdout|all]
    args = sys.argv[1:]
    half = args.pop() if args and args[-1] in ("tune", "holdout", "all") else "tune"
    main(args[0], args[1] if len(args) > 1 else None, half)

"""Link each file number to its row in the prior summary, for scoring only.

This link never carries a value into the workbook. It exists so score.py can find
the labelled answer for a document, and it is written once so that what matched,
and what could not, is on the record rather than recomputed silently.
"""
import json, os, sys

import openpyxl

from ids import FILE_RX

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = "Authorization_Summary"
FILE_COLUMN_HEADER = "DFO_File_or_PATH"


def link(xlsx, segs_path=None):
    ws = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h or "") for h in rows[0]]
    col = header.index(FILE_COLUMN_HEADER)

    segs = json.load(open(segs_path or os.path.join(HERE, "segs.json")))
    doc_fns = {s["file_no"] for s in segs}

    matched, unmatchable = {}, []
    for i, row in enumerate(rows[1:], start=2):
        found = FILE_RX.findall(str(row[col] or ""))
        if not found:
            unmatchable.append({"row": i, "why": "no file number on the prior row"})
        elif found[0] not in doc_fns:
            unmatchable.append({"row": i, "file_number": found[0],
                                "why": "names a file number no document carries"})
        else:
            matched.setdefault(found[0], []).append(i)
    return {"matched": matched, "unmatchable": unmatchable,
            "unlabelled": sorted(doc_fns - set(matched))}


if __name__ == "__main__":
    xlsx = sys.argv[1] if len(sys.argv) > 1 else \
        json.load(open(os.path.join(HERE, "release.json")))["prior_summary"]
    out = link(xlsx)
    json.dump(out, open(os.path.join(HERE, "prior_rows.json"), "w"), indent=1)
    print(f"  matched      {len(out['matched'])} file numbers to prior rows")
    print(f"  unmatchable  {len(out['unmatchable'])} prior rows")
    for u in out["unmatchable"]:
        print(f"                 row {u['row']}: {u['why']}")
    print(f"  unlabelled   {len(out['unlabelled'])} file numbers have no prior row")
    dupes = {k: v for k, v in out["matched"].items() if len(v) > 1}
    if dupes:
        print(f"  two prior rows for one file number: {dupes}")

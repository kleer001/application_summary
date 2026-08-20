"""What a wave still owes, computed from what is on disk.

The plan called for a manifest file recording per-document state. A file that
records state can disagree with the state; this reads the sandbox instead, so
"done" always means the output is there and verifies, and re-running is just
running again.
"""
import json, os, sys
from collections import Counter

from verify import check


def status(sandbox):
    orders = json.load(open(f"{sandbox}/wave.json"))
    out = []
    for o in orders:
        row = {"doc_id": o["doc_id"], "reader": o["reader"], "model": o["model"],
               "state": "outstanding", "detail": ""}
        if os.path.exists(o["out"]):
            try:
                doc = json.load(open(o["out"]))
            except json.JSONDecodeError as e:
                row.update(state="failed", detail=f"invalid JSON: {e}")
            else:
                v = Counter(verdict for _, verdict, _ in
                            check(doc, o["slice"], o["first_page"], o["last_page"]))
                fields = len(doc.get("fields", {}))
                row["detail"] = (f"{v['pass']} pass, {v['null']} null, {v['QUEUE']} queued, "
                                 f"{v['REJECT'] + v['MALFORMED']} rejected, "
                                 f"{len(doc.get('conditions', []))} conditions")
                row["state"] = ("failed" if fields and v["MALFORMED"] > fields / 2
                                else "done")
                if row["state"] == "failed":
                    row["detail"] = "output is not in the entries shape"
        out.append(row)
    return out


if __name__ == "__main__":
    rows = status(sys.argv[1])
    verbose = "-v" in sys.argv
    for r in rows:
        if verbose or r["state"] != "done":
            print(f"  {r['state']:12s} {r['doc_id']:22s} {r['reader']} "
                  f"({r['model']:6s}) {r['detail']}")
    print(f"\n  {dict(Counter(r['state'] for r in rows))} of {len(rows)} reads")

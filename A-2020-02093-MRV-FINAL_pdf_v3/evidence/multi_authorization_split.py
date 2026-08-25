"""Does `build.split_by_authorization` give each authorization only its own figures?

`19-HCAA-01437#429` is the one letter in this release that grants several
authorizations and sorts its impacts under them, so it is the only case in the
corpus that exercises the split. This holds the attribution the document prints
on page 2 beside the reader answers taken before the contract asked for it, and
checks that each authorization comes out with the figures the document gives it
and none of the others.

Run from the repository root. Exits non-zero if any row takes a figure that
belongs to another authorization.
"""
import json, sys
S = "A-2020-02093-MRV-FINAL_pdf_v3"
sys.path.insert(0, S)
from build import split_by_authorization, cell

READ = f"{S}/run2/superseded/19-HCAA-01437_429.a1.ce97b09d0a03.json"

# what page 2 prints, under its own headings
SAYS = {
    "hadd_destruction_m2": {649: "19-HCAA-01437", 578: "19-HCAA-01675",
                            125: "19-HCAA-01714", 1752: "19-HCAA-01714", 364: "19-HCAA-01714"},
    "hadd_alteration_m2":  {1724: "19-HCAA-01437", 2411: "19-HCAA-01675",
                            437: "19-HCAA-01714", 62: "19-HCAA-01714"},
    "hadd_disturbance_m2": {40: "19-HCAA-01437", 170: "19-HCAA-01675",
                            640: "19-HCAA-01714", 155: "19-HCAA-01714", 80: "19-HCAA-01714"},
}

src = json.load(open(READ))["fields"]
fields = {}
for name, f in src.items():
    entries = [dict(e) for e in (f.get("entries") or [])]
    for e in entries:
        where = SAYS.get(name, {}).get(e.get("value"))
        if where:
            e["authorization"] = where
    fields[name] = entries

rows = split_by_authorization({"fields": fields, "documents": [], "conditions": []})
print(f"{len(rows)} rows\n")
ok = True
for r in rows:
    n = r["authorization"]
    print(f"  {n}")
    print(f"      DFO_File_or_PATH     {cell(r['fields']['file_number'])}")
    for name in SAYS:
        got = cell(r["fields"].get(name) or [])
        want = "; ".join(str(v) for v, a in SAYS[name].items() if a == n) or None
        flag = "ok " if str(got) == str(want) else "FAIL"
        if flag == "FAIL":
            ok = False
        print(f"      {flag} {name:22s} {got}   (document says: {want})")
    print(f"      proponent (shared)   {str(cell(r['fields'].get('proponent') or []))[:46]}")
print("\nPASS" if ok else "\nFAIL")
sys.exit(0 if ok else 1)

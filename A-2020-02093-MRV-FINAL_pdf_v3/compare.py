"""Compare two readers over one document and bucket every field.

Formatting is not disagreement. 'Alberta' and 'AB', '65 m2' and '65 m²', and the
same answer given once as a value and once as a single component are all folded
before counting, the same way verify.py folds OCR noise before matching. A
comparison that counts formatting reports a working specification as broken.

Buckets: agree, both_null, superset (one answer contains the other, which the
plan resolves in favour of the fuller), one_null, differ.
"""
import json, re, sys

from combine import contains, values
from norm import norm

PROV = {"ab": "alberta", "bc": "britishcolumbia", "mb": "manitoba", "nb": "newbrunswick",
        "nl": "newfoundlandandlabrador", "ns": "novascotia", "nt": "northwestterritories",
        "nu": "nunavut", "on": "ontario", "pe": "princeedwardisland", "qc": "quebec",
        "sk": "saskatchewan", "yt": "yukon"}
def fold(v):
    """One scalar answer, reduced to what it actually asserts."""
    return PROV.get(norm(v), norm(v))


def answer(f):
    """A field is its entries, folded to what they assert."""
    return {fold(e["value"]) for e in values(f)} - {""}


def compare(a_path, b_path):
    A, B = json.load(open(a_path)), json.load(open(b_path))
    fa, fb = A.get("fields", {}), B.get("fields", {})
    buckets, rows = {"agree": 0, "both_null": 0, "superset": 0, "one_null": 0, "differ": 0}, []
    for k in sorted(set(fa) | set(fb)):
        sa, sb = answer(fa.get(k)), answer(fb.get(k))
        if not sa and not sb:
            buckets["both_null"] += 1
        elif sa == sb:
            buckets["agree"] += 1
        elif not sa or not sb:
            buckets["one_null"] += 1
            rows.append(("one_null", k, sa, sb))
        elif sa < sb or sb < sa or contains(sa, sb):
            buckets["superset"] += 1
            rows.append(("superset", k, sa, sb))
        else:
            buckets["differ"] += 1
            rows.append(("differ", k, sa, sb))
    ca = {c.get("number") for c in A.get("conditions", [])}
    cb = {c.get("number") for c in B.get("conditions", [])}
    return buckets, rows, (len(ca), len(cb), len(ca & cb), sorted(ca - cb), sorted(cb - ca))


if __name__ == "__main__":
    buckets, rows, (na, nb, shared, aonly, bonly) = compare(sys.argv[1], sys.argv[2])
    print(f"  fields   {buckets}")
    print(f"  numbered conditions  A {na}  B {nb}  shared {shared}")
    if aonly:
        print(f"    A only: {aonly}")
    if bonly:
        print(f"    B only: {bonly}")
    for kind, k, sa, sb in rows:
        print(f"\n  {kind.upper():9s} {k}")
        print(f"      A {sorted(sa) if sa else 'null'}")
        print(f"      B {sorted(sb) if sb else 'null'}")

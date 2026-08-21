"""Turn two readers' answers into one answer, or into a queue entry.

Agreement for bounded fields, union for enumeration. The asymmetry is the point:
two readers naming different figures have disagreed, but two readers listing
different numbers of conditions have not — one of them stopped early.
"""
import re

from adjudicate import adjudicate

OK = ("pass", "null", "QUEUE")
from norm import norm as fold

def values(field):
    return [e for e in (field or {}).get("entries") or []
            if isinstance(e, dict) and e.get("value") not in (None, "")]


def covers(sa, sb):
    """Does every answer in sb appear inside some answer in sa?

    Two readers quoting the same clause to different lengths are not two
    readings. One quoted it; the other abbreviated, which the contract forbids
    but which still names the same fact on the same page. Containment is checked
    entry by entry, on the folded text, where character order survives and
    spacing and punctuation do not.
    """
    if not sa or not sb or len(sa) < len(sb):
        return False
    used = set()
    for y in sorted(sb):                               # greedy over a set is seed-dependent
        if len(y) < 8:
            return False                       # too short to be evidence of anything
        hit = next((x for x in sorted(sa) if x not in used and (y in x or x in y)), None)
        if hit is None:
            return False
        used.add(hit)
    return True


def contains(sa, sb):
    """Either side wholly accounted for by the other."""
    return covers(sa, sb) or covers(sb, sa)


def combine_field(fa, fb, verdict_a, verdict_b):
    """One field, two readers.

    Returns (entries, note, resolved). A note records what happened; `resolved`
    says whether the rules settled it. Only the unresolved need a person, so the
    two are kept apart rather than filed together as "queue".
    """
    # Three verdicts are answers, not failures. "null" is the reader saying the
    # document is silent. "QUEUE" is a quote the reader read off the scan that
    # the OCR layer does not carry — the expected outcome on a mangled page, and
    # the reason the scan is given to readers at all. Only REJECT and MALFORMED
    # are a failure to verify.
    ok_a, ok_b = verdict_a in OK, verdict_b in OK
    ea, eb = values(fa) if ok_a else [], values(fb) if ok_b else []

    if not ok_a and not ok_b:
        return [], f"neither reader verified ({verdict_a} / {verdict_b})", False
    if not ea and not eb:
        ra = (fa or {}).get("reason")
        rb = (fb or {}).get("reason")
        if ok_a and ok_b and ra != rb:
            return [], f"both null, different reasons: {ra} / {rb}", False
        return [], None, True                              # agreed null

    entries, verdict, note = adjudicate(ea, eb)
    return entries, note, verdict != "conflict"


def norm_number(n):
    """4.2, 42 and 4,2 are one condition number."""
    return ".".join(re.findall(r"\d+", str(n or "")))


def union_conditions(ca, cb):
    """Every numbered item either reader found, at the finest numbering used."""
    seen = {}
    for c in list(ca or []) + list(cb or []):
        key = norm_number(c.get("number"))
        if not key:
            continue
        if key not in seen:
            seen[key] = dict(c)
        elif len(str(c.get("text") or "")) > len(str(seen[key].get("text") or "")):
            seen[key].update(c)                            # keep the fuller text

    folded = {k: fold(c.get("text")) for k, c in seen.items()}
    kept = []
    for key, c in seen.items():
        children = [k for k in folded if k != key and k.startswith(key + ".")]
        covered = "".join(folded[k] for k in children)
        if children and folded[key] and folded[key][:40] in covered:
            continue                                       # a parent its children carry
        kept.append(c)
    return sorted(kept, key=lambda c: [int(x) for x in norm_number(c["number"]).split(".")])
